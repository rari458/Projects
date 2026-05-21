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

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "AMD", "INTC", "TSM", "QCOM"]

def fetch_data(tickers, start, end):
    print(f"  [Data] Downloading {len(tickers)} assets...")
    df = yf.download(tickers, start=start, end=end, progress=False)

    if isinstance(df.columns, pd.MultiIndex):
        close_df = df["Close"]
    else:
        close_df = df

    prices = {}
    for col in close_df.columns:
        prices[col] = close_df[col].dropna().tolist()
    return prices

def run_pca_scan():
    print("\n=======================================================")
    print(" 🧠 PCA STAT-ARB: Extracting Latent Market Factors")
    print("=======================================================")

    prices = fetch_data(TICKERS, "2023-01-01", "2024-01-01")

    print("  [System] Feeding data to C++ Eigen Matrix Solver...")

    res = fe.PCAArbitrage.calculate_signals(prices, 1)

    if not res.explained_variance:
        print("  [Error] Failed to calculate PCA. Check data lengths.")
        return

    print(f"\n  [PCA Variance Explained by PC1]: {res.explained_variance[0]*100:.2f}%\n")

    print("-" * 45)
    print(f"  {'Symbol':<10} | {'Z-Score:<10'} | {'Action':<15}")
    print("-" * 45)

    sorted_signals = sorted(res.z_scores.items(), key=lambda x: x[1])

    for sym, z in sorted_signals:
        action = "WAIT"
        if z > 2.0:
            action = "🔴 SELL (Overbought)"
        elif z < -2.0:
            action = "🟢 BUY (Oversold)"

        print(f"  {sym:<10} | {z:>10.4f} | {action:<15}")
    print("-" * 45)

if __name__ == "__main__":
    run_pca_scan()