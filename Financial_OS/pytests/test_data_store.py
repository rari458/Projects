import os

import pandas as pd
import psycopg
import pytest

import data_store

# A separate database on the same server, so tests never touch market data.
# Locally that is the Compose postgres service; CI starts its own container.
TEST_DSN = os.environ.get("FOS_TEST_DATABASE_URL",
                          "postgresql://fos:fos@localhost:5433/fos_test")

@pytest.fixture(scope="session")
def dsn():
    # Create the test database if needed. No skip when the server is down: a test
    # suite that silently skips its database tests would pass without running them.
    info = psycopg.conninfo.conninfo_to_dict(TEST_DSN)
    admin = psycopg.conninfo.make_conninfo(TEST_DSN, dbname="postgres")
    with psycopg.connect(admin, autocommit=True) as c:
        exists = c.execute("SELECT 1 FROM pg_database WHERE datname = %s",
                           [info["dbname"]]).fetchone()
        if not exists:
            c.execute(f'CREATE DATABASE "{info["dbname"]}"')
    return TEST_DSN

@pytest.fixture
def con(dsn):
    c = data_store.connect(dsn)
    c.execute("TRUNCATE ohlc")
    yield c
    c.close()

def _insert(con, symbol, date, o, h, l, c):
    con.execute(
        "INSERT INTO ohlc VALUES (%s, %s, %s, %s, %s, %s)",
        [symbol, date, o, h, l, c],
    )

def _dates(result):
    return [d.strftime("%Y-%m-%d") for d in result["dates"]]

def _count(con):
    return con.execute("SELECT COUNT(*) FROM ohlc").fetchone()[0]

def test_connect_creates_ohlc_table(con):
    tables = con.execute("SELECT table_name FROM information_schema.tables "
                         "WHERE table_schema = 'public'").fetchall()
    assert ("ohlc",) in tables

def test_get_ohlc_round_trip(con):
    _insert(con, "AAPL", "2020-01-02", 1, 2, 0.5, 1.5)
    _insert(con, "AAPL", "2020-01-01", 1, 2, 0.5, 1.4)

    result = data_store.get_ohlc(con, "AAPL")

    assert _dates(result) == ["2020-01-01", "2020-01-02"]
    assert result["closes"] == [1.4, 1.5]

def test_get_ohlc_filters_by_symbol(con):
    _insert(con, "AAPL", "2020-01-01", 1, 2, 0.5, 1.5)
    _insert(con, "MSFT", "2020-01-01", 10, 20, 5, 15)

    result = data_store.get_ohlc(con, "AAPL")

    assert result["closes"] == [1.5]

def test_get_ohlc_filters_by_start_and_end(con):
    for d in ("2020-01-01", "2020-01-02", "2020-01-03"):
        _insert(con, "AAPL", d, 1, 2, 0.5, 1.5)

    result = data_store.get_ohlc(con, "AAPL", start="2020-01-02", end="2020-01-02")

    assert _dates(result) == ["2020-01-02"]

def test_get_ohlc_empty_when_symbol_unknown(con):
    result = data_store.get_ohlc(con, "NOPE")
    assert result["dates"]  == []
    assert result["closes"] == []

def test_symbols_aggregates_counts_and_date_range(con):
    _insert(con, "AAPL", "2020-01-01", 1, 2, 0.5, 1.5)
    _insert(con, "AAPL", "2020-01-02", 1, 2, 0.5, 1.5)
    _insert(con, "MSFT", "2020-06-01", 10, 20, 5, 15)

    df = data_store.symbols(con).set_index("symbol")

    assert df.loc["AAPL", "bars"] == 2
    assert df.loc["MSFT", "bars"] == 1
    assert df.loc["AAPL", "first"].strftime("%Y-%m-%d") == "2020-01-01"
    assert df.loc["AAPL", "last"].strftime("%Y-%m-%d") == "2020-01-02"

def test_get_returns_matrix_computes_pct_change(con):
    closes = {"2020-01-01": 100.0, "2020-01-02": 110.0, "2020-01-03": 121.0}
    for d, c in closes.items():
        _insert(con, "AAPL", d, 0, 0, 0, c)

    returns = data_store.get_returns_matrix(con, ["AAPL"])

    assert [round(v, 4) for v in returns["AAPL"]] == [0.10, 0.10]

def test_get_returns_matrix_drops_dates_missing_any_symbol(con):
    _insert(con, "AAPL", "2020-01-01", 0, 0, 0, 100.0)
    _insert(con, "AAPL", "2020-01-02", 0, 0, 0, 110.0)
    _insert(con, "AAPL", "2020-01-03", 0, 0, 0, 121.0)
    _insert(con, "MSFT", "2020-01-01", 0, 0, 0, 200.0)
    _insert(con, "MSFT", "2020-01-03", 0, 0, 0, 220.0)

    returns = data_store.get_returns_matrix(con, ["AAPL", "MSFT"])

    assert len(returns) == 1
    assert round(returns["AAPL"].iloc[0], 4) == 0.21
    assert round(returns["MSFT"].iloc[0], 4) == 0.10

def test_get_aligned_ohlc_drops_dates_missing_any_symbol(con):
    for d, c in (("2020-01-01", 100.0), ("2020-01-02", 110.0), ("2020-01-03", 121.0)):
        _insert(con, "AAPL", d, 1, 2, 0.5, c)
    for d, c in (("2020-01-01", 200.0), ("2020-01-03", 220.0)):
        _insert(con, "MSFT", d, 1, 2, 0.5, c)

    dates, bars = data_store.get_aligned_ohlc(con, ["AAPL", "MSFT"])

    assert [d.strftime("%Y-%m-%d") for d in dates] == ["2020-01-01", "2020-01-03"]
    # Truncating to the shorter series fed AAPL's 2020-01-02 bar (110.0) on the
    # same tick as MSFT's 2020-01-03 bar.
    assert bars["AAPL"]["closes"] == [100.0, 121.0]
    assert bars["MSFT"]["closes"] == [200.0, 220.0]

def test_get_aligned_ohlc_starts_at_the_latest_first_date(con):
    # MSFT listed (or was ingested) one day later than AAPL.
    for d, c in (("2020-01-01", 100.0), ("2020-01-02", 110.0), ("2020-01-03", 121.0)):
        _insert(con, "AAPL", d, 1, 2, 0.5, c)
    for d, c in (("2020-01-02", 200.0), ("2020-01-03", 220.0)):
        _insert(con, "MSFT", d, 1, 2, 0.5, c)

    dates, bars = data_store.get_aligned_ohlc(con, ["AAPL", "MSFT"])

    assert [d.strftime("%Y-%m-%d") for d in dates] == ["2020-01-02", "2020-01-03"]
    assert bars["AAPL"]["closes"] == [110.0, 121.0]
    assert bars["MSFT"]["closes"] == [200.0, 220.0]

def _fake_download(multiindex=False):
    dates = pd.date_range("2020-01-01", periods=3, freq="D")
    df = pd.DataFrame(
        {
            "Open": [100.0, 101.0, 102.0],
            "High": [105.0, 106.0, 107.0],
            "Low": [95.0, 96.0, 97.0],
            "Close": [102.0, 103.0, 104.0],
        },
        index=dates,
    )
    if multiindex:
        df.columns = pd.MultiIndex.from_product([df.columns, ["AAPL"]])
    return df

def test_ingest_flattens_multiindex_and_inserts_rows(con, dsn, monkeypatch):
    monkeypatch.setattr(
        data_store.yf, "download", lambda *a, **k: _fake_download(multiindex=True)
    )

    assert data_store.ingest_symbols(["AAPL"], dsn=dsn) == ({"AAPL": 3}, {})
    assert data_store.get_ohlc(con, "AAPL")["closes"] == [102.0, 103.0, 104.0]

def test_ingest_reports_a_symbol_without_data_as_failed(con, dsn, monkeypatch):
    monkeypatch.setattr(data_store.yf, "download", lambda *a, **k: pd.DataFrame())

    inserted, failed = data_store.ingest_symbols(["NOPE"], dsn=dsn)

    assert inserted == {}
    assert "NOPE" in failed

def test_ingest_counts_only_rows_it_added(con, dsn, monkeypatch):
    monkeypatch.setattr(data_store.yf, "download", lambda *a, **k: _fake_download())

    first = data_store.ingest_symbols(["AAPL"], dsn=dsn)
    again = data_store.ingest_symbols(["AAPL"], dsn=dsn)

    assert first == ({"AAPL": 3}, {})
    # ON CONFLICT DO NOTHING skips all three, and the count says so.
    assert again == ({"AAPL": 0}, {})
    assert _count(con) == 3

def test_ingest_partitions_ok_and_failed(con, dsn, monkeypatch):
    def fake_download(symbol, *a, **k):
        if symbol == "AAPL":
            return _fake_download()
        raise ValueError(f"yfinance returned no data for {symbol!r}")

    monkeypatch.setattr(data_store.yf, "download", fake_download)

    inserted, failed = data_store.ingest_symbols(["AAPL", "BAD"], dsn=dsn)

    assert inserted == {"AAPL": 3}
    assert "BAD" in failed

def test_ingest_is_all_or_nothing(con, dsn, monkeypatch):
    monkeypatch.setattr(data_store.yf, "download", lambda *a, **k: _fake_download())
    real_insert = data_store._insert

    def insert_then_fail_on_msft(c, tidy):
        if tidy["symbol"].iloc[0] == "MSFT":
            raise RuntimeError("disk full")
        return real_insert(c, tidy)
    monkeypatch.setattr(data_store, "_insert", insert_then_fail_on_msft)

    with pytest.raises(RuntimeError):
        data_store.ingest_symbols(["AAPL", "MSFT"], dsn=dsn)

    # AAPL was inserted before MSFT failed, and was rolled back with it.
    assert _count(con) == 0

def test_a_reader_neither_waits_for_nor_sees_an_uncommitted_ingest(con, dsn):
    _insert(con, "AAPL", "2020-01-01", 1, 2, 0.5, 1.5)
    tidy = pd.DataFrame({"symbol": "MSFT", "date": [pd.Timestamp("2020-01-01").date()],
                         "open": [1.0], "high": [2.0], "low": [0.5], "close": [1.5]})

    with data_store.connect(dsn) as writer:
        with writer.transaction():
            data_store._insert(writer, tidy)
            # The writer holds its transaction open. With DuckDB this reader would
            # have failed to open the file at all (ENGINEERING_DECISIONS #14).
            with data_store.connect_readonly(dsn) as reader:
                assert data_store.symbols(reader)["symbol"].tolist() == ["AAPL"]
        with data_store.connect_readonly(dsn) as reader:
            assert data_store.symbols(reader)["symbol"].tolist() == ["AAPL", "MSFT"]

def test_readonly_connection_rejects_writes(con, dsn):
    with data_store.connect_readonly(dsn) as reader:
        with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
            _insert(reader, "AAPL", "2020-01-01", 1, 2, 0.5, 1.5)
