# data_store.py

import os
import psycopg
import yfinance as yf
import pandas as pd

# Containers set FOS_DATABASE_URL to the Compose (or k8s) Postgres service. The
# default reaches the Compose service from the host, where its port is published.
DEFAULT_DSN = "postgresql://fos:fos@localhost:5433/market"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS ohlc (
    symbol TEXT             NOT NULL,
    date   DATE             NOT NULL,
    open   DOUBLE PRECISION,
    high   DOUBLE PRECISION,
    low    DOUBLE PRECISION,
    close  DOUBLE PRECISION,
    PRIMARY KEY (symbol, date)
);
"""

def _dsn(dsn):
    return dsn or os.environ.get("FOS_DATABASE_URL", DEFAULT_DSN)

def connect(dsn=None):
    # Autocommit: every statement commits on its own unless it runs inside an
    # explicit `with con.transaction():` block, which is how writes are grouped.
    con = psycopg.connect(_dsn(dsn), autocommit=True)
    con.execute(_SCHEMA)
    return con

def connect_readonly(dsn=None):
    # The server rejects any write on this connection. Unlike DuckDB's read-only
    # mode it takes no file lock, so readers and the writer never wait for each other.
    return psycopg.connect(_dsn(dsn), autocommit=True,
                           options="-c default_transaction_read_only=on")

def _frame(con, query, params=()):
    cur = con.execute(query, params)
    return pd.DataFrame(cur.fetchall(), columns=[c.name for c in cur.description])

def _flatten_yf(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def _download(symbol, period="5y", interval="1d"):
    raw = yf.download(symbol, period=period, interval=interval, progress=False)
    if raw.empty:
        raise ValueError(f"yfinance returned no data for {symbol!r}")
    raw = _flatten_yf(raw)

    return pd.DataFrame({
        "symbol": symbol,
        "date":   pd.to_datetime(raw.index).date,
        "open":   raw["Open"].astype(float).values,
        "high":   raw["High"].astype(float).values,
        "low":    raw["Low"].astype(float).values,
        "close":  raw["Close"].astype(float).values,
    })

def _insert(con, tidy):
    # Must run inside a transaction: the staging table empties itself on commit.
    # COPY into it, then one INSERT ... ON CONFLICT DO NOTHING, whose row count is
    # exactly the rows that were new.
    con.execute("CREATE TEMP TABLE IF NOT EXISTS ohlc_stage "
                "(LIKE ohlc) ON COMMIT DELETE ROWS")
    with con.cursor().copy("COPY ohlc_stage (symbol, date, open, high, low, close) "
                           "FROM STDIN") as copy:
        for row in tidy[["symbol", "date", "open", "high", "low", "close"]].itertuples(index=False):
            copy.write_row(row)
    added = con.execute("INSERT INTO ohlc SELECT * FROM ohlc_stage "
                        "ON CONFLICT DO NOTHING").rowcount
    con.execute("TRUNCATE ohlc_stage")
    return added

def ingest_symbols(symbols, period="5y", interval="1d", dsn=None):
    # Download everything first, with no connection open, then write it all in one
    # transaction: readers see the whole ingest or none of it, and never wait for
    # it (Postgres serves them the last committed rows). A second writer inserting
    # the same rows waits on the primary key and then skips them, so concurrent
    # ingests cannot lose rows. Returns ({symbol: rows added}, {symbol: error}).
    frames, failed = {}, {}
    for sym in symbols:
        try:
            frames[sym] = _download(sym, period=period, interval=interval)
        except Exception as exc:
            failed[sym] = str(exc)
    if not frames:
        return {}, failed

    with connect(dsn) as con, con.transaction():
        inserted = {sym: _insert(con, tidy) for sym, tidy in frames.items()}
    return inserted, failed

def get_ohlc(con, symbol, start=None, end=None):
    query = "SELECT date, open, high, low, close FROM ohlc WHERE symbol = %s"
    params = [symbol]
    if start is not None:
        query += " AND date >= %s"
        params.append(start)
    if end is not None:
        query += " AND date <= %s"
        params.append(end)
    query += " ORDER BY date"

    df = _frame(con, query, params)
    return {
        "dates":  df["date"].tolist(),
        "opens":  df["open"].tolist(),
        "highs":  df["high"].tolist(),
        "lows":   df["low"].tolist(),
        "closes": df["close"].tolist(),
    }

def get_aligned_ohlc(con, symbols, start=None, end=None):
    # A backtest feeds bar i of every symbol as one tick, so bar i must be the same
    # date for all of them. Keep only the dates every symbol has: a date missing for
    # one symbol (a gap, a later listing, an ingest run on another day) is dropped
    # for all, the same rule get_returns_matrix applies.
    if not symbols: raise ValueError("need at least one symbol")
    series = {sym: get_ohlc(con, sym, start=start, end=end) for sym in symbols}
    dates = sorted(set.intersection(*(set(s["dates"]) for s in series.values())))
    aligned = {}
    for sym, s in series.items():
        row = {d: i for i, d in enumerate(s["dates"])}
        aligned[sym] = {key: [s[key][row[d]] for d in dates] for key in ("opens", "highs", "lows", "closes")}
    return dates, aligned

def symbols(con):
    return _frame(con, """
        SELECT symbol, COUNT(*) AS bars, MIN(date) AS first, MAX(date) AS last
        FROM ohlc GROUP BY symbol ORDER BY symbol
    """)

def get_returns_matrix(con, symbols, start=None, end=None):
    query = "SELECT date, symbol, close FROM ohlc WHERE symbol = ANY(%s)"
    params = [list(symbols)]
    if start is not None:
        query += " AND date >= %s"
        params.append(start)
    if end is not None:
        query += " AND date <= %s"
        params.append(end)

    df = _frame(con, query, params)
    wide = df.pivot(index="date", columns="symbol", values="close").dropna()
    returns = wide.pct_change(fill_method=None).dropna()
    return returns[list(symbols)]
