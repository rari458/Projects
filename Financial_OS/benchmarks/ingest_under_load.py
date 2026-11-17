#!/usr/bin/env python3
"""Worker reads under concurrent writes, on the running Compose stack.

Submits a batch of backtest jobs through the gateway and, while the workers
are busy with them, keeps writing to data/market.duckdb in one of three ways:

  none      no writes (baseline)
  snapshot  POST /ingest repeatedly: the ingester writes a copy and swaps it in
  inplace   open the live file read-write from this process, hold it, close

Every backtest task opens the database read-only. The script reports how the
jobs ended, how many task attempts Celery made (a DuckDB lock conflict makes a
task retry, up to 3 times), and, for the writers, how long each write took.

Attempts come from the change in celery_tasks_total in Prometheus, summed over
every status label, so retries are counted as attempts minus jobs. (Until the
fix after ENGINEERING_DECISIONS #14, a retry was labelled "failure", so the
status label alone could not tell them apart.)

Run from the repo root (inplace mode opens data/market.duckdb from the venv).
"""

import argparse
import json
import threading
import time
import urllib.parse
import urllib.request

DB = "data/market.duckdb"
TASK = "run_backtest_job"


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


def _attempts(prom):
    return _prom_scalar(prom, f'sum(celery_tasks_total{{task_name="{TASK}"}})')


def _replicas(prom):
    return int(_prom_scalar(prom, 'count(up{job="worker"} == 1)'))


def _wait(gateway, job_id, poll):
    while True:
        status = _get(f"{gateway}/jobs/{job_id}")
        if status["state"] in ("SUCCESS", "FAILURE"):
            return status
        time.sleep(poll)


def _load(gateway, n, body, poll, out):
    t0 = time.perf_counter()
    ids = [_post(f"{gateway}/jobs", body)["job_id"] for _ in range(n)]
    states, errors = {}, {}
    for job_id in ids:
        status = _wait(gateway, job_id, poll)
        states[status["state"]] = states.get(status["state"], 0) + 1
        if status["state"] == "FAILURE":
            err = status.get("error", "")[:70]
            errors[err] = errors.get(err, 0) + 1
    out.update(states=states, errors=errors, wall=time.perf_counter() - t0)


def _write_snapshot(gateway, poll):
    t0 = time.perf_counter()
    job_id = _post(f"{gateway}/ingest", {"symbols": ["SPY"], "period": "1mo"})["job_id"]
    status = _wait(gateway, job_id, poll)
    ok = status["state"] == "SUCCESS"
    return {"ok": ok, "seconds": time.perf_counter() - t0,
            "detail": status.get("result", {}).get("inserted") if ok else status.get("error")}


def _write_inplace(hold):
    import duckdb  # only this mode needs it
    t0, tries = time.perf_counter(), 0
    while True:
        tries += 1
        try:
            con = duckdb.connect(DB)
            break
        except duckdb.Error:
            time.sleep(0.005)
    acquired = time.perf_counter() - t0
    time.sleep(hold)  # a writer that needs the file for `hold` seconds
    con.close()
    return {"ok": True, "seconds": time.perf_counter() - t0,
            "detail": f"lock after {acquired:.2f}s / {tries} tries, held {hold}s"}


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--mode", choices=("none", "snapshot", "inplace"), required=True)
    p.add_argument("--jobs", type=int, default=2000)
    p.add_argument("--hold", type=float, default=5.0,
                   help="inplace mode: seconds each writer keeps the file open")
    p.add_argument("--pause", type=float, default=1.0, help="seconds between writes")
    p.add_argument("--poll", type=float, default=0.02)
    p.add_argument("--settle", type=float, default=15.0,
                   help="seconds to wait for Prometheus to scrape the last tasks")
    p.add_argument("--gateway", default="http://localhost:8001")
    p.add_argument("--prometheus", default="http://localhost:9090")
    a = p.parse_args()

    body = {"symbols": ["SPY", "QQQ", "XLK"], "start": "2021-07-01"}
    before = _attempts(a.prometheus)

    load = {}
    t = threading.Thread(target=_load, args=(a.gateway, a.jobs, body, a.poll, load))
    t.start()
    writes = []
    time.sleep(1.0)  # let the queue fill before the first write
    while a.mode != "none" and t.is_alive():
        if a.mode == "snapshot":
            writes.append(_write_snapshot(a.gateway, a.poll))
        else:
            writes.append(_write_inplace(a.hold))
        time.sleep(a.pause)
    t.join()

    time.sleep(a.settle)
    attempts = int(round(_attempts(a.prometheus) - before))
    jobs = sum(load["states"].values())
    print(f"mode={a.mode} workers={_replicas(a.prometheus)} jobs={jobs} "
          f"wall {load['wall']:.1f}s ({jobs / load['wall']:.0f} jobs/s) | "
          f"outcomes {load['states']} | attempts {attempts} (retries {attempts - jobs})")
    for err, n in load["errors"].items():
        print(f"   {n} x {err}")
    for i, w in enumerate(writes, 1):
        print(f"   write {i}: {'ok' if w['ok'] else 'FAILED'} in {w['seconds']:.2f}s  {w['detail']}")


if __name__ == "__main__":
    main()
