# data_pipeline.py

import sys
import os
import yfinance as yf
import pandas as pd

# Append the directory containing the compiled .so file
sys.path.append(os.path.abspath('./build/src'))

try:
    import FinancialEngine
except ImportError as e:
    print(f"[Error] Failed to import FinancialEngine C++ Core: {e}")
    sys.exit(1)

def main():
    print("==================================================")
    print("  Aladdin-Killer: Real-World Data Pipeline Test   ")
    print("==================================================")

    #1. Initialize C++ Engine with MACD Strategy
    initial_capital = 100000.0
    strategy_name = "MACD"

    print(f"-> Booting C++ Engine with Strategy: {strategy_name}")
    engine = FinancialEngine.Backtester(initial_capital, strategy_name, 1.0)

    #2. Fetch Real Market Data via Python
    ticker = "SPY"
    print(f"-> Fetching real market data for {ticker} via yfinance...")
    data = yf.download(ticker, period="1y", interval="1d", progress=False)

    if data.empty:
        print("[Error] Failed to fetch data.")
        return

    print(f"-> Successfully fetched {len(data)} trading days. Streaming to C++ Core...")

    # 3. Stream Data to C++ Engine
    for index, row in data.iterrows():
        timestamp = index.timestamp()

        # yfinance returns multi-index columns in recent versions, handle it gracefully
        open_p = float(row['Open'].iloc[0]) if isinstance(row['Open'], pd.Series) else float(row['Open'])
        high_p = float(row['High'].iloc[0]) if isinstance(row['High'], pd.Series) else float(row['High'])
        low_p = float(row['Low'].iloc[0]) if isinstance(row['Low'], pd.Series) else float(row['Low'])
        close_p = float(row['Close'].iloc[0]) if isinstance(row['Close'], pd.Series) else float(row['Close'])

        # Inject into C++
        engine.on_market_data(ticker, timestamp, open_p, high_p, low_p, close_p)

    # 4. Extract Real Backtest Results
    print("\n==================================================")
    print("  Backtest Execution Complete (Real Data)         ")
    print("==================================================")
    print(f"Final Equity: ${engine.get_total_equity():.2f}")
    print(f"Final Cash:   ${engine.get_cash_balance():.2f}")
    print(f"Holdings ({ticker}):  {engine.get_holdings(ticker):.2f} shares")
    print(f"Max Drawdown: {engine.get_max_drawdown() * 100:.2f}%")

    trades = engine.get_trade_history()
    print(f"Total Trades Executed by C++ MACD: {len(trades)}")

if __name__ == "__main__":
    main()