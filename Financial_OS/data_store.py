# data_store.py

import duckdb
import yfinance as yf
import pandas as pd

DEFAULT_DB = "market.duckdb"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS ohlc (
    symbol VARCHAR NOT NULL,
    date   DATE    NOT NULL,
    open   DOUBLE,
    high   DOUBLE,
    low    DOUBLE,
    close  DOUBLE,
    PRIMARY KEY (symbol, date)
);
"""

def connect(db_path=DEFAULT_DB):
    con = duckdb.connect(db_path)
    con.execute(_SCHEMA)
    return con

def connect_readonly(db_path=DEFAULT_DB):
    return duckdb.connect(db_path, read_only=True)

def _flatten_yf(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def ingest(con, symbol, period="5y", interval="1d"):
    raw = yf.download(symbol, period=period, interval=interval, progress=False)
    if raw.empty:
        raise ValueError(f"yfinance returned no data for {symbol!r}")
    raw = _flatten_yf(raw)

    tidy = pd.DataFrame({
        "symbol": symbol,
        "date":   pd.to_datetime(raw.index).date,
        "open":   raw["Open"].astype(float).values,
        "high":   raw["High"].astype(float).values,
        "low":    raw["Low"].astype(float).values,
        "close":  raw["Close"].astype(float).values,
    })

    con.register("tidy_df", tidy)
    con.execute("""
        INSERT INTO ohlc
        SELECT symbol, date, open, high, low, close FROM tidy_df
        ON CONFLICT DO NOTHING
    """)
    con.unregister("tidy_df")
    return len(tidy)

def get_ohlc(con, symbol, start=None, end=None):
    query = "SELECT date, open, high, low, close FROM ohlc WHERE symbol = ?"
    params = [symbol]
    if start is not None:
        query += " AND date >= ?"
        params.append(start)
    if end is not None:
        query += " AND date <= ?"
        params.append(end)
    query += " ORDER BY date"

    df = con.execute(query, params).fetchdf()
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
    if not symbols: raise ValueError("need at lease one symbol")
    series = {sym: get_ohlc(con, sym, start=start, end=end) for sym in symbols}
    dates = sorted(set.intersection(*(set(s["dates"]) for s in series.values())))
    aligned = {}
    for sym, s in series.items():
        row = {d: i for i, d in enumerate(s["dates"])}
        aligned[sym] = {key: [s[key][row[d]] for d in dates] for key in ("opens", "highs", "lows", "closes")}
    return dates, aligned

def symbols(con):
    return con.execute("""
        SELECT symbol, COUNT(*) AS bars, MIN(date) AS first, MAX(date) AS last
        FROM ohlc GROUP BY symbol ORDER BY symbol
    """).fetchdf()

def get_returns_matrix(con, symbols, start=None, end=None):
    placeholders = ", ".join(["?"] * len(symbols))
    query = f"SELECT date, symbol, close FROM ohlc WHERE symbol IN ({placeholders})"
    params = list(symbols)
    if start is not None:
        query += " AND date >= ?"
        params.append(start)
    if end is not None:
        query += " AND date <= ?"
        params.append(end)

    df = con.execute(query, params).fetchdf()
    wide = df.pivot(index="date", columns="symbol", values="close").dropna()
    returns = wide.pct_change(fill_method=None).dropna()
    return returns[list(symbols)]

def ingest_many(con, symbols, period="5y", interval="1d"):
    ok, failed = {}, {}
    for sym in symbols:
        try:
            ok[sym] = ingest(con, sym, period=period, interval=interval)
        except Exception as exc:
            failed[sym] = str(exc)
    return ok, failed