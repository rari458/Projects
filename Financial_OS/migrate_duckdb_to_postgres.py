#!/usr/bin/env python3
"""One-off copy of data/market.duckdb into the Postgres database.

Reads every ohlc row with DuckDB (read-only) and writes them all through
data_store._insert in one transaction. Then it reads both sides back in the same
order and compares them row by row, floats included, so a passing run means the
Postgres table holds exactly what DuckDB held. Safe to re-run: rows that are
already there are skipped.

Run from the repo root with the Compose postgres service up:
    python migrate_duckdb_to_postgres.py [--duckdb data/market.duckdb] [--dsn URL]
"""

import argparse
import sys

import duckdb
import pandas as pd

import data_store

QUERY = "SELECT symbol, date, open, high, low, close FROM ohlc ORDER BY symbol, date"


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--duckdb", default="data/market.duckdb")
    p.add_argument("--dsn", default=None,
                   help="default: FOS_DATABASE_URL, else the local Compose service")
    a = p.parse_args()

    src = duckdb.connect(a.duckdb, read_only=True)
    rows = src.execute(QUERY).fetchdf()
    src.close()
    rows["date"] = pd.to_datetime(rows["date"]).dt.date

    with data_store.connect(a.dsn) as con:
        with con.transaction():
            added = data_store._insert(con, rows)
        dst = con.execute(QUERY).fetchall()

    src_rows = [tuple(r) for r in rows.itertuples(index=False)]
    print(f"{a.duckdb}: {len(src_rows)} rows, {rows['symbol'].nunique()} symbols")
    print(f"postgres: {len(dst)} rows after inserting {added}")

    wanted = set(rows["symbol"])  # built once: inside the comprehension it was O(n^2)
    mine = [r for r in dst if r[0] in wanted]
    if mine == src_rows:
        print("identical: every row matches, floats included")
        return 0
    diff = next(i for i, (x, y) in enumerate(zip(src_rows, mine)) if x != y) \
        if len(mine) == len(src_rows) else min(len(mine), len(src_rows))
    print(f"MISMATCH at row {diff}: duckdb {src_rows[diff] if diff < len(src_rows) else None}"
          f" vs postgres {mine[diff] if diff < len(mine) else None}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
