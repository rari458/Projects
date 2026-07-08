# optimizer_compare.py

import FinancialEngine
import data_store

UNIVERSE = [
    "SPY", "QQQ", "XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB",
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "JPM", "JNJ", "XOM",
    "PG", "KO", "HD", "V", "MA", "UNH",
]

def report(name, result):
    gross = sum(abs(w) for w in result.optimal_weights)
    shorts = sum(1 for w in result.optimal_weights if w < 0)
    print(f"\n-> {name}")
    print(f"   Expected return (ann.): {result.portfolio_return * 100:6.2f}%")
    print(f"   Volatility (ann.):      {result.portfolio_volatility * 100:6.2f}%")
    print(f"   Sharpe ratio:           {result.sharpe_ratio:6.3f}")
    print(f"   Gross exposure:         {gross * 100:6.1f}%  ({shorts} short legs)")

def main():
    con = data_store.connect()
    data_store.ingest_many(con, UNIVERSE, period="5y")

    rets = data_store.get_returns_matrix(con, UNIVERSE, start="2021-07-01")
    print(f"-> {len(UNIVERSE)} symbols, {len(rets)} aligned trading days")

    opt = FinancialEngine.Optimizer()
    for sym in UNIVERSE:
        opt.add_asset(sym, rets[sym].tolist())

    mc = opt.optimize_sharpe_ratio(200000, 0.02, 0)
    analytic = opt.optimize_max_sharpe_analytic(0.02)

    report("Random-search Monte Carlo (200k trials, long-only)", mc)
    report("Analytic tangency (closed-form, may short/lever)", analytic)

    lift = (analytic.sharpe_ratio - mc.sharpe_ratio) / mc.sharpe_ratio * 100.0
    print(f"\n-> Analytic tangency Sharpe is {lift:.1f}% above random search.")
    print("   (Gap = random-search inefficiency + the relaxed long/short constraint.)")

    con.close()

if __name__ == "__main__":
    main()