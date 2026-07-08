# optimize_demo.py

import FinancialEngine
import data_store

def main():
    con = data_store.connect()
    universe = ["SPY", "AAPL", "MSFT"]

    rets = data_store.get_returns_matrix(con, universe, start="2021-07-01")
    print(f"-> Aligned {len(rets)} trading days across {len(universe)} symbols")

    opt = FinancialEngine.Optimizer()
    for sym in universe:
        opt.add_asset(sym, rets[sym].tolist())

    result = opt.optimize_sharpe_ratio(100000, 0.02, 0)

    print("\n-> Max-Sharpe portfolio (100k trials, parallel):")
    for sym, w in zip(universe, result.optimal_weights):
        print(f"   {sym}: {w * 100:5.1f}%")

    print(f"\n   Expected return (ann.): {result.portfolio_return * 100:.2f}%")
    print(f"   Volatility (ann.):      {result.portfolio_volatility * 100:.2f}%")
    print(f"   Sharpe ratio:           {result.sharpe_ratio:.3f}")

    con.close()

if __name__ == "__main__":
    main()