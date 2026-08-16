# services/metrics.py
"""Worker-side Prometheus metrics.

Imported by every worker via `include` in celery_app.py. The HTTP server
starts on the worker_ready signal (not at import time) so that merely
importing the Celery app never binds a port.
"""

import time

from celery.signals import task_postrun, task_prerun, worker_ready
from prometheus_client import Counter, Histogram, start_http_server

TASKS_TOTAL = Counter(
    "celery_tasks_total",
    "Finished Celery tasks by name and outcome",
    ["task_name", "status"],
)

TASK_DURATION = Histogram(
    "celery_task_duration_seconds",
    "Wall-clock execution time per task (excludes queue wait)",
    ["task_name"],
    # Measured distribution: 59/60 tasks landed in a single (0.01, 0.025]
    # bucket, leaving quantiles uninterpolatable. Resolution is concentrated
    # in the 7.5-35 ms band where the work actually lives; decision #9's
    # 24.7 ms was a fitted per-task cost including broker round-trip; the
    # in-worker figure this histogram measures is ~16.8 ms (decision #12).
    buckets=(0.005, 0.01, 0.0125, 0.015, 0.0175, 0.02, 0.0225, 0.025, 0.03, 0.04, 0.05, 0.1, 0.25, 0.5, 1.0, 5.0),
)

# --pool=solo runs tasks single-threaded in this process, so a plain dict
# needs no lock.
_task_start: dict[str, float] = {}

@worker_ready.connect
def _start_metrics_server(**_):
    # The exporter runs on a daemon thread inside the solo worker; a scrape
    # can stall while a C++ call holds the GIL (decision #7), which is
    # acceptable at ~17 ms task sizes.
    start_http_server(9100)

@task_prerun.connect
def _record_start(task_id=None, **_):
    _task_start[task_id] = time.perf_counter()

@task_postrun.connect
def _record_done(task_id=None, task=None, state=None, **_):
    started = _task_start.pop(task_id, None)
    if started is not None:
        TASK_DURATION.labels(task.name).observe(time.perf_counter() - started)
    TASKS_TOTAL.labels(task.name, "success" if state == "SUCCESS" else "failure").inc()