#!/usr/bin/env python3
"""Worker reads under concurrent writes, on the running Compose stack.

Submits a batch of backtest jobs through the gateway and, while the workers
are busy with them, keeps writing to the Postgres market database in one of
these ways:

  none       no writes (baseline)
  ingest     POST /ingest repeatedly: the ingester commits one transaction each
  longtx     from this process, open a write transaction that inserts a fake
             symbol and updates every SPY row the backtests read, hold it open
             for --hold seconds, then roll it back (nothing is left behind)
  exclusive  from this process, LOCK TABLE ohlc IN ACCESS EXCLUSIVE MODE for
             --hold seconds, then roll back: the kind of lock a TRUNCATE or an
             ALTER TABLE takes, and the one ordinary writes never take

Every backtest task opens the database read-only. The script reports how the
jobs ended, how many task attempts Celery made, and how long each write took.
Attempts come from the change in celery_tasks_total in Prometheus, summed over
every status label, so retries are counted as attempts minus jobs.

ENGINEERING_DECISIONS #14 measured the DuckDB-era version of this script
(modes none, snapshot and inplace, commit 1bc301e); its inplace mode held a
DuckDB write lock on a file the workers no longer read, so it was removed.

Run from the repo root with the venv active (longtx and exclusive need psycopg).
"""

import argparse
import datetime
import json
import threading
import time
import urllib.parse
import urllib.request

TASK = "run_backtest_job"
DSN = "postgresql://fos:fos@localhost:5433/market"


def _post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r)


def _get(url):
    with urllib.request.urlopen(url, timeout=30) as r:
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


def _write_ingest(gateway, poll):
    t0 = time.perf_counter()
    job_id = _post(f"{gateway}/ingest", {"symbols": ["SPY"], "period": "1mo"})["job_id"]
    status = _wait(gateway, job_id, poll)
    ok = status["state"] == "SUCCESS"
    return {"ok": ok, "seconds": time.perf_counter() - t0,
            "detail": status.get("result", {}).get("inserted") if ok else status.get("error")}


def _write_longtx(dsn, hold):
    import psycopg
    day = datetime.date(2000, 1, 3)
    fake = [("ZZLOAD", day + datetime.timedelta(days=i), 1.0, 1.0, 1.0, 1.0)
            for i in range(1255)]
    t0 = time.perf_counter()
    with psycopg.connect(dsn) as con:
        with con.transaction(force_rollback=True):
            with con.cursor() as cur:
                cur.executemany("INSERT INTO ohlc VALUES (%s, %s, %s, %s, %s, %s)", fake)
                cur.execute("UPDATE ohlc SET close = close WHERE symbol = 'SPY'")
                updated = cur.rowcount
            ready = time.perf_counter() - t0
            time.sleep(hold)  # row locks on every SPY row, uncommitted, for `hold` s
    return {"ok": True, "seconds": time.perf_counter() - t0,
            "detail": f"{len(fake)} rows inserted, {updated} SPY rows updated in "
                      f"{ready:.2f}s, held open {hold}s, rolled back"}


def _write_exclusive(dsn, hold):
    import psycopg
    t0 = time.perf_counter()
    with psycopg.connect(dsn) as con:
        with con.transaction(force_rollback=True):
            con.execute("LOCK TABLE ohlc IN ACCESS EXCLUSIVE MODE")
            got = time.perf_counter() - t0
            time.sleep(hold)
    return {"ok": True, "seconds": time.perf_counter() - t0,
            "detail": f"ACCESS EXCLUSIVE after {got:.2f}s, held {hold}s"}


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--mode", choices=("none", "ingest", "longtx", "exclusive"), required=True)
    p.add_argument("--jobs", type=int, default=2000)
    p.add_argument("--hold", type=float, default=5.0,
                   help="longtx/exclusive: seconds the transaction stays open")
    p.add_argument("--pause", type=float, default=1.0, help="seconds between writes")
    p.add_argument("--poll", type=float, default=0.02)
    p.add_argument("--settle", type=float, default=15.0,
                   help="seconds to wait for Prometheus to scrape the last tasks")
    p.add_argument("--gateway", default="http://localhost:8001")
    p.add_argument("--prometheus", default="http://localhost:9090")
    p.add_argument("--dsn", default=DSN, help="longtx/exclusive: the market database")
    a = p.parse_args()

    body = {"symbols": ["SPY", "QQQ", "XLK"], "start": "2021-07-01"}
    before = _attempts(a.prometheus)

    load = {}
    t = threading.Thread(target=_load, args=(a.gateway, a.jobs, body, a.poll, load))
    t.start()
    writes = []
    time.sleep(1.0)  # let the queue fill before the first write
    while a.mode != "none" and t.is_alive():
        if a.mode == "ingest":
            writes.append(_write_ingest(a.gateway, a.poll))
        elif a.mode == "longtx":
            writes.append(_write_longtx(a.dsn, a.hold))
        else:
            writes.append(_write_exclusive(a.dsn, a.hold))
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
