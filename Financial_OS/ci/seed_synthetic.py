"""Seed the Compose stack's market database with a fixed synthetic series.

CI cannot rely on reaching Yahoo Finance, so the smoke test (ci/smoke_test.py)
runs against three made-up symbols, ZZSYN1 to ZZSYN3, with 300 business days of
seeded random-walk prices from 2023-01-02 to 2024-02-23. Run it inside a worker
container, where data_store and FOS_DATABASE_URL are already set up:

    docker compose exec -T worker python - < ci/seed_synthetic.py

It refuses to run against a database that already holds real symbols, so it
cannot mix fake prices into market data. Re-running it adds nothing.
"""

import numpy as np
import pandas as pd

import data_store

SYMBOLS = ["ZZSYN1", "ZZSYN2", "ZZSYN3"]
DAYS = pd.bdate_range("2023-01-02", periods=300)

con = data_store.connect()
real = con.execute("SELECT COUNT(*) FROM ohlc WHERE symbol NOT LIKE %s",
                   ["ZZSYN%"]).fetchone()[0]
if real:
    raise SystemExit(f"refusing to seed: the database already holds {real} rows of real symbols")

rng = np.random.default_rng(7)
frames = []
for i, sym in enumerate(SYMBOLS):
    n = len(DAYS)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0003 * (i + 1), 0.01, n)))
    open_ = close * (1.0 + rng.normal(0.0, 0.002, n))
    high = np.maximum(open_, close) * (1.0 + np.abs(rng.normal(0.0, 0.003, n)))
    low = np.minimum(open_, close) * (1.0 - np.abs(rng.normal(0.0, 0.003, n)))
    frames.append(pd.DataFrame({"symbol": sym, "date": DAYS.date, "open": open_,
                                "high": high, "low": low, "close": close}))

with con.transaction():
    added = {f["symbol"].iloc[0]: data_store._insert(con, f) for f in frames}
con.close()
print("seeded rows:", added)
