import pandas as pd
import pytest

import data_store

@pytest.fixture
def con():
    return data_store.connect(":memory:")

def _insert(con, symbol, date, o, h, l, c):
    con.execute(
        "INSERT INTO ohlc VALUES (?, ?, ?, ?, ?, ?)",
        [symbol, date, o, h, l, c],
    )

def _dates(result):
    return [d.strftime("%Y-%m-%d") for d in result["dates"]]

def test_connect_creates_ohlc_table():
    c = data_store.connect(":memory:")
    tables = c.execute("SELECT table_name FROM information_schema.tables").fetchall()
    assert("ohlc",) in tables

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

def test_ingest_flattens_multiindex_and_inserts_rows(con, monkeypatch):
    monkeypatch.setattr(
        data_store.yf, "download", lambda *a, **k: _fake_download(multiindex=True)
    )

    n = data_store.ingest(con, "AAPL")

    assert n == 3
    result = data_store.get_ohlc(con, "AAPL")
    assert result["closes"] == [102.0, 103.0, 104.0]

def test_ingest_raises_on_empty_data(con, monkeypatch):
    monkeypatch.setattr(data_store.yf, "download", lambda *a, **k: pd.DataFrame())

    with pytest.raises(ValueError):
        data_store.ingest(con, "NOPE")

def test_ingest_is_idempotent_on_conflict(con, monkeypatch):
    monkeypatch.setattr(data_store.yf, "download", lambda *a, **k: _fake_download())

    data_store.ingest(con, "AAPL")
    data_store.ingest(con, "AAPL")

    count = con.execute("SELECT COUNT(*) FROM ohlc").fetchone()[0]
    assert count == 3

def test_ingest_many_partitions_ok_and_failed(con, monkeypatch):
    def fake_download(symbol, *a, **k):
        if symbol == "AAPL":
            return _fake_download()
        raise ValueError(f"yfinance returned no data for {symbol!r}")

    monkeypatch.setattr(data_store.yf, "download", fake_download)

    ok, failed = data_store.ingest_many(con, ["AAPL", "BAD"])

    assert ok == {"AAPL": 3}
    assert "BAD" in failed
    
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
def _count(db_path):
    con = data_store.connect_readonly(str(db_path))
    try:
        return con.execute("SELECT COUNT(*) FROM ohlc").fetchone()[0]
    finally:
        con.close()

def test_ingest_snapshot_creates_db_and_counts_inserted_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(data_store.yf, "download", lambda *a, **k: _fake_download())
    db = tmp_path / "data" / "market.duckdb"

    first = data_store.ingest_snapshot(["AAPL"], db_path=str(db))
    again = data_store.ingest_snapshot(["AAPL"], db_path=str(db))

    assert first == ({"AAPL": 3}, {})
    # ON CONFLICT DO NOTHING skips all three, and the count says so.
    assert again == ({"AAPL": 0}, {})
    assert _count(db) == 3

def test_ingest_snapshot_is_not_blocked_by_an_open_reader(tmp_path, monkeypatch):
    monkeypatch.setattr(data_store.yf, "download", lambda *a, **k: _fake_download())
    db = tmp_path / "market.duckdb"
    data_store.ingest_snapshot(["AAPL"], db_path=str(db))

    reader = data_store.connect_readonly(str(db))
    # A read-write open of the live file would fail here; the snapshot never opens it.
    data_store.ingest_snapshot(["MSFT"], db_path=str(db))
    # The open reader keeps the file it opened...
    assert reader.execute("SELECT COUNT(*) FROM ohlc").fetchone()[0] == 3
    reader.close()
    # ...and the next open sees the swapped-in one.
    assert _count(db) == 6

def test_ingest_snapshot_failure_leaves_live_file_and_no_temp(tmp_path, monkeypatch):
    monkeypatch.setattr(data_store.yf, "download", lambda *a, **k: _fake_download())
    db = tmp_path / "market.duckdb"
    data_store.ingest_snapshot(["AAPL"], db_path=str(db))

    def broken_insert(con, tidy):
        raise RuntimeError("disk full")
    monkeypatch.setattr(data_store, "_insert", broken_insert)

    with pytest.raises(RuntimeError):
        data_store.ingest_snapshot(["MSFT"], db_path=str(db))

    assert _count(db) == 3
    assert sorted(p.name for p in tmp_path.iterdir()) == [".ingest.lock", "market.duckdb"]

def test_ingest_snapshot_skips_the_swap_when_every_download_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(data_store.yf, "download", lambda *a, **k: _fake_download())
    db = tmp_path / "market.duckdb"
    data_store.ingest_snapshot(["AAPL"], db_path=str(db))
    inode = db.stat().st_ino

    monkeypatch.setattr(data_store.yf, "download", lambda *a, **k: pd.DataFrame())
    inserted, failed = data_store.ingest_snapshot(["NOPE"], db_path=str(db))

    assert inserted == {}
    assert "NOPE" in failed
    assert db.stat().st_ino == inode
