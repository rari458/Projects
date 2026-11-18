#!/usr/bin/env python3
"""End-to-end smoke test of the Compose stack, as CI runs it.

Expects the stack to be up and seeded by ci/seed_synthetic.py. Through the
gateway it checks a 3-symbol backtest over the seeded series, a walk-forward
(which fans out through a Celery chord), a closed-form optimize job, and the
ingest route. The ingest asks for a ticker that cannot exist, so the outcome does
not depend on reaching Yahoo: the job must succeed and report the symbol as
failed, which proves the request reached the ingester through its own queue.
Stdlib only. Exits non-zero if any check fails.

    python3 ci/smoke_test.py [http://localhost:8001]
"""

import json
import math
import sys
import time
import urllib.request

GW = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8001"
SYMBOLS = ["ZZSYN1", "ZZSYN2", "ZZSYN3"]
failures = 0


def post(path, body):
    req = urllib.request.Request(GW + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r)


def wait(submitted, timeout=180):
    job_id, t0 = submitted["job_id"], time.time()
    while True:
        with urllib.request.urlopen(f"{GW}/jobs/{job_id}", timeout=10) as r:
            status = json.load(r)
        if status["state"] in ("SUCCESS", "FAILURE"):
            return status
        if time.time() - t0 > timeout:
            return {"state": "TIMEOUT", "error": f"still {status['state']} after {timeout}s"}
        time.sleep(0.5)


def check(name, ok, detail):
    global failures
    failures += not ok
    print(f"{'ok  ' if ok else 'FAIL'} {name}: {detail}")


with urllib.request.urlopen(GW + "/health", timeout=10) as r:
    health = json.load(r)
check("gateway health", health == {"status": "ok"}, health)

s = wait(post("/jobs", {"symbols": SYMBOLS}))
res = s.get("result") or {}
equity = res.get("final_equity")
check("backtest", s["state"] == "SUCCESS" and res.get("bars") == 300
      and isinstance(equity, float) and math.isfinite(equity),
      f"{s['state']}, bars={res.get('bars')}, trades={res.get('total_trades')}, "
      f"equity={equity} {s.get('error', '')}")

sub = post("/walkforward", {"symbols": SYMBOLS, "start": "2023-01-02", "end": "2024-02-23"})
s = wait(sub)
res = s.get("result") or {}
check("walk-forward (chord)", s["state"] == "SUCCESS" and sub.get("num_windows") == 4
      and res.get("num_windows") == 4,
      f"{s['state']}, windows submitted={sub.get('num_windows')} "
      f"aggregated={res.get('num_windows')} {s.get('error', '')}")

s = wait(post("/optimize", {"symbols": SYMBOLS, "method": "min_variance"}))
weights = (s.get("result") or {}).get("weights") or {}
check("optimize (min_variance)", s["state"] == "SUCCESS" and set(weights) == set(SYMBOLS)
      and all(math.isfinite(w) for w in weights.values()),
      f"{s['state']}, weights={ {k: round(v, 4) for k, v in weights.items()} } "
      f"{s.get('error', '')}")

s = wait(post("/ingest", {"symbols": ["ZZNOSUCHTICKER"], "period": "1mo"}))
res = s.get("result") or {}
check("ingest route", s["state"] == "SUCCESS" and "ZZNOSUCHTICKER" in res.get("failed", {}),
      f"{s['state']}, inserted={res.get('inserted')}, "
      f"failed={list(res.get('failed', {}))} {s.get('error', '')}")

print("all checks passed" if not failures else f"{failures} check(s) failed")
sys.exit(1 if failures else 0)
