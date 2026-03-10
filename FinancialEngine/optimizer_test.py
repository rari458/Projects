import sys
import os
import yfinance as yf
import pandas as pd

sys.path.append(os.path.abspath("build/src"))

try:
    import FinancialEngine as fe
except ImportError as e:
    print(f"[Error] Failed to load C++ Core: {e}")
    sys.exit(1)

TICKERS = ["SPY", "QQQ", "TLT", "GLD"]
RISK_FREE_RATE = 0.04

def fetch_returns(tickers, start, end):
    print(f"  [Data] Downloading {len(tickers)} assets ({start} ~ {end})...")
    df = yf.download(tickers, start=start, end=end, progress=False)

    if isinstance(df.columns, pd.MultiIndex):
        close_df = df["Close"]
    else:
        close_df = df

    close_df = close_df.dropna()
    returns_df = close_df.pct_change().dropna()
    return returns_df

def print_result(title, result, tickers):
    print(f"\n  [{title}]")
    print("-" * 45)
    print(f"  > Expected Return: {result.portfolio_return * 100:>7.2f}%")
    print(f"  > Expected Vol:    {result.portfolio_volatility * 100:>7.2f}%")
    print(f"  > Sharpe Ratio:    {result.sharpe_ratio:>7.4f}")
    print("-" * 45)
    print("  [Optimal Weights]")
    for i, ticker in enumerate(tickers):
        print(f"    - {ticker:<5}: {result.optimal_weights[i] * 100:>6.2f}%")
    print("-" * 45)

def run_optimizer_test():
    print("\n=======================================================")
    print(" 🧠 PORTFOLIO OPTIMIZER: BATTLE OF THE ALGORITHMS")
    print("=======================================================")

    returns_df = fetch_returns(TICKERS, "2018-01-01", "2023-12-31")

    opt = fe.Optimizer()

    print("  [System] Feeding return vectors to C++ Engine...")
    for ticker in TICKERS:
        ret_list = returns_df[ticker].tolist()
        opt.add_asset(ticker, ret_list)

    print("  [System] Computing optimizations...\n")

    res_sharpe = opt.optimize_sharpe_ratio(50000, RISK_FREE_RATE)

    res_inv_vol = opt.optimize_inverse_volatility(RISK_FREE_RATE)

    res_min_var = opt.optimize_minimum_variance(RISK_FREE_RATE)

    print_result("Method A: Max Sharpe (Monte Carlo)", res_sharpe, TICKERS)
    print_result("Method B: Risk Parity (Inverse Volatility)", res_inv_vol, TICKERS)
    print_result("Method C: Global Minimum Variance (Eigen)", res_min_var, TICKERS)

if __name__ == "__main__":
    run_optimizer_test()