#!/usr/bin/env python3
"""Throughput of POST /optimize on the running Compose stack.

Submits a batch of identical mc_sharpe jobs through the gateway, waits for all
of them, and prints wall-clock throughput plus the exact mean in-worker task
time. The mean comes from the change in the worker histogram's _sum and _count
in Prometheus, which (unlike a quantile) does not depend on bucket boundaries.

Run once per setting. The replica count is whatever
`docker compose up -d --scale worker=K` last set; the script reads it back
from Prometheus and prints it.
"""

import argparse
import json
import time
import urllib.parse
import urllib.request

UNIVERSE = ["AAPL", "AMZN", "GOOGL", "HD", "JNJ", "JPM", "KO", "MA", "META", "MSFT",
            "NVDA", "PG", "QQQ", "SPY", "UNH", "V", "XLB", "XLE", "XLF", "XLI",
            "XLK", "XLP", "XLU", "XLV", "XLY", "XOM"]


def _post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r)


def _get(url):
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.load(r)


def _prom_scalar(prom, query):
    url = f"{prom}/api/v1/query?" + urllib.parse.urlencode({"query": query})
    result = _get(url)["data"]["result"]
    return float(result[0]["value"][1]) if result else 0.0


def _worker_totals(prom):
    sel = '{task_name="run_optimize_job"}'
    return (_prom_scalar(prom, f"sum(celery_task_duration_seconds_sum{sel})"),
            _prom_scalar(prom, f"sum(celery_task_duration_seconds_count{sel})"))


def _submit(gateway, n, body):
    return [_post(f"{gateway}/optimize", body)["job_id"] for _ in range(n)]


def _wait_all(gateway, job_ids, poll):
    # Jobs finish in roughly submission order, so waiting on them in order keeps
    # each poll to a single GET; a job that finished early costs one call.
    for job_id in job_ids:
        while True:
            status = _get(f"{gateway}/jobs/{job_id}")
            if status["state"] == "SUCCESS":
                break
            if status["state"] == "FAILURE":
                raise SystemExit(f"job {job_id} failed: {status.get('error')}")
            time.sleep(poll)


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--num-threads", type=int, choices=(0, 1), required=True)
    p.add_argument("--jobs", type=int, default=120)
    p.add_argument("--warmup", type=int, default=24,
                   help="untimed jobs first, so every replica has imported the module, "
                        "opened DuckDB and built its thread pool")
    p.add_argument("--num-simulations", type=int, default=100000)
    p.add_argument("--symbols", default=",".join(UNIVERSE))
    p.add_argument("--poll", type=float, default=0.02, help="seconds between status checks")
    p.add_argument("--settle", type=float, default=15.0,
                   help="seconds to wait so Prometheus has rediscovered and scraped every "
                        "replica (scrape 5 s, DNS refresh 10 s)")
    p.add_argument("--gateway", default="http://localhost:8001")
    p.add_argument("--prometheus", default="http://localhost:9090")
    a = p.parse_args()

    symbols = a.symbols.split(",")
    body = {"symbols": symbols, "start": "2021-07-01", "method": "mc_sharpe",
            "num_simulations": a.num_simulations, "num_threads": a.num_threads}

    _wait_all(a.gateway, _submit(a.gateway, a.warmup, body), a.poll)
    time.sleep(a.settle)
    replicas = int(_prom_scalar(a.prometheus, 'count(up{job="worker"} == 1)'))
    sum0, count0 = _worker_totals(a.prometheus)

    t0 = time.perf_counter()
    _wait_all(a.gateway, _submit(a.gateway, a.jobs, body), a.poll)
    wall = time.perf_counter() - t0

    time.sleep(a.settle)
    sum1, count1 = _worker_totals(a.prometheus)
    seen = round(count1 - count0)

    print(f"workers={replicas} num_threads={a.num_threads} jobs={a.jobs} "
          f"symbols={len(symbols)} sims={a.num_simulations} | "
          f"wall {wall:.2f} s | {a.jobs / wall:.1f} jobs/s | "
          f"in-worker mean {1000 * (sum1 - sum0) / max(seen, 1):.1f} ms/task")
    if seen != a.jobs:
        print(f"  warning: Prometheus saw {seen} tasks, not {a.jobs}; a replica restarted "
              f"or was not scraped, so the in-worker mean is not trustworthy for this run")


if __name__ == "__main__":
    main()
