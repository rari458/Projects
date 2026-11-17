# services/tests/test_metrics.py

import pytest
from prometheus_client import REGISTRY
from services import metrics

class _Task:
    name = "metrics_test_task"

def _count(status):
    labels = {"task_name": _Task.name, "status": status}
    return REGISTRY.get_sample_value("celery_tasks_total", labels) or 0.0

@pytest.mark.parametrize("state, status", [
    ("SUCCESS", "success"),
    ("RETRY", "retry"),      # was counted as "failure" (ENGINEERING_DECISIONS #14)
    ("FAILURE", "failure"),
])
def test_postrun_counts_each_state_under_its_own_label(state, status):
    before = {s: _count(s) for s in ("success", "retry", "failure")}
    metrics._record_done(task_id="t", task=_Task(), state=state)
    after = {s: _count(s) for s in ("success", "retry", "failure")}
    assert {s: after[s] - before[s] for s in after} == {
        s: (1.0 if s == status else 0.0) for s in after}
