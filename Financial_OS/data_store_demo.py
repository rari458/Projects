# data_store_demo.py

import FinancialEngine
import data_store

def main():
    universe = ["SPY", "AAPL", "MSFT"]
    print("-> Ingesting universe into Postgres (idempotent)...")
    # One transaction per ingest: readers, the Compose workers included, see all of
    # it or none of it, and never wait for it.
    inserted, failed = data_store.ingest_symbols(universe, period="5y")
    for sym in universe:
        print(f"   {sym}: {inserted.get(sym, 0)} new bars", failed.get(sym, ""))

    con = data_store.connect_readonly()

    print("\n-> Stored universe:")
    print(data_store.symbols(con).to_string(index=False))

    sym = "AAPL"
    bars = data_store.get_ohlc(con, sym, start="2020-01-01", end="2024-12-31")
    print(f"\n-> Sliced {len(bars['closes'])} bars of {sym}; streaming to C++ core...")

    engine = FinancialEngine.Backtester(100000.0, "MACD", 1.0)
    for i in range(len(bars["closes"])):
        engine.on_market_data(
            sym, float(i),
            bars["opens"][i], bars["highs"][i], bars["lows"][i], bars["closes"][i],
        )

    print(f"   Final equity: ${engine.get_total_equity():.2f}")
    print(f"   Max drawdown: {engine.get_max_drawdown() * 100:.2f}%")
    print(f"   Trades:       {len(engine.get_trade_history())}")

    con.close()

if __name__ == "__main__":
    main()
