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

def fetch_aligned_data(tickers, start, end):
    print(f"  [Data] Downloading {len(tickers)} assets and aligning timestamps...")
    df = yf.download(tickers, start=start, end=end, progress=False)["Close"]
    df = df.dropna()
    return df

def run_stat_arb_backtest():
    print("\n=======================================================")
    print(" 🧠 MULTI-ASSET PCA STAT-ARB BACKTEST")
    print("=======================================================")

    df = fetch_aligned_data(TICKERS, "2020-01-01", "2023-12-31")

    initial_capital = 100000.0
    engine = fe.Backtester(initial_capital, "PCA", 2.0)

    engine.set_regime_filter(False)

    print(f"  [System] Engine initialized. Feeding {len(df)} trading days to C++ Core...")

    for i, (date, row) in enumerate(df.iterrows()):
        timestamp = float(i)
        for ticker in TICKERS:
            price = float(row[ticker])
            engine.on_market_data(ticker, timestamp, price, price, price, price)

    equity = engine.get_total_equity()
    mdd = engine.get_max_drawdown()
    trades = engine.get_trade_history()

    ret_pct = (equity - initial_capital) / initial_capital * 100.0

    print("\n=======================================================")
    print(" 📊 PCA STAT-ARB PERFORMANCE REPORT")
    print("=======================================================")
    print(f"  > Final Equity: ${equity:.2f}")
    print(f"  > Total Return: {ret_pct:.2f}%")
    print(f"  > Max Drawdown: {mdd*100:.2f}%")
    print(f"  > Total Trades: {len(trades)}")
    print("=======================================================\n")

if __name__ == "__main__":
    run_stat_arb_backtest()