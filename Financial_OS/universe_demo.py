# universe_demo.py

import FinancialEngine
import data_store

UNIVERSE = [
    "SPY", "QQQ", "XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB",
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "JPM", "JNJ", "XOM",
    "PG", "KO", "HD", "V", "MA", "UNH",
]

def main():
    con = data_store.connect()

    print(f"-> Batch-ingesting {len(UNIVERSE)} symbols into DuckDB (idempotent)...")
    ok, failed = data_store.ingest_many(con, UNIVERSE, period="5y")
    print(f"   {len(ok)} ok, {len(failed)} failed")
    for sym, err in failed.items():
        print(f"   ! {sym}: {err}")

    universe = list(ok.keys())
    rets = data_store.get_returns_matrix(con, universe, start="2021-07-01")
    print(f"\n-> Aligned {len(rets)} trading days across {len(universe)} symbols")

    opt = FinancialEngine.Optimizer()
    for sym in universe:
        opt.add_asset(sym, rets[sym].tolist())

    result = opt.optimize_sharpe_ratio(200000, 0.02, 0)

    ranked = sorted(zip(universe, result.optimal_weights), key=lambda kv: -kv[1])
    print("\n-> Max-Sharpe portfolio (200k trials, parallel) -- top 10 holdings:")
    for sym, w in ranked[:10]:
        print(f"   {sym:5s} {w * 100:5.1f}%")

    print(f"\n   Expected return (ann.): {result.portfolio_return * 100:.2f}%")
    print(f"   Volatility (ann.):      {result.portfolio_volatility * 100:.2f}%")
    print(f"   Sharpe ratio:           {result.sharpe_ratio:.3f}")

    con.close()

if __name__ == "__main__":
    main()