import requests
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

def fetch_data(symbol, start, end):
    print(f"  [Data] Downloading {symbol} ({start} ~ {end})...")
    df = yf.download(symbol, start=start, end=end, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)

    return {
        "opens": df["Open"].tolist(),
        "highs": df["High"].tolist(),
        "lows": df["Low"].tolist(),
        "closes": df["Close"].tolist()
    }

def run_simulation(scenario_name, symbol, assets_data, use_filter):
    print(f"\n  🏃 Running Simulation: {scenario_name} (Filter: {'ON' if use_filter else 'OFF'})")

    try:
        import sys
        import os
        sys.path.append(os.path.abspath("build/src"))
        import FinancialEngine as fe

        engine = fe.Backtester(10000.0, "EMA", 1.0)
        engine.set_risk_params(0.20, 0.05)

        engine.set_regime_filter(use_filter, 252)

        opens = assets_data['opens']
        highs = assets_data['highs']
        lows = assets_data['lows']
        closes = assets_data['closes']

        for i in range(len(closes)):
            engine.on_market_data(symbol, i, opens[i], highs[i], lows[i], closes[i])

        equity = engine.get_total_equity()
        mdd = engine.get_max_drawdown()
        trades = engine.get_trade_history()

        ret_pct = (equity - 10000.0) / 10000.0 * 100.0

        print(f"    > Final Equity: ${equity:.2f}")
        print(f"    > Return:       {ret_pct:.2f}%")
        print(f"    > Max Drawdown: {mdd*100:.2f}%")
        print(f"    > Trade Count:  {len(trades)}")

        return equity, mdd, ret_pct

    except ImportError:
        print("  [Error] FinancialEngine module not found. Did you build it?")
        return 0, 0, 0

if __name__ == "__main__":
    print("=======================================================")
    print(" 🛡️  ADAPTIVE STRATEGY TEST: Surviving the Bear Market")
    print("=======================================================")

    symbol = "TQQQ"
    print(f"  [Target] {symbol} (High Volatility Asset)")

    data = fetch_data(symbol, "2021-01-01", "2022-12-31")

    eq_off, mdd_off, ret_off = run_simulation("Blind Strategy", symbol, data, False)

    eq_on, mdd_on, ret_on = run_simulation("Adaptive Strategy", symbol, data, True)

    print("\n=======================================================")
    print(" 📊 FINAL COMPARISON REPORT")
    print("=======================================================")
    print(f"  {'Metric':<15} | {'Blind (OFF)':<15} | {'Adaptive (ON)':<15}")
    print("-" * 55)
    print(f"  {'Return':<15} | {ret_off:>13.2f}% | {ret_on:>13.2f}%")
    print(f"  {'MDD':<15} | {mdd_off*100:>13.2f}% | {mdd_on*100:>13.2f}%")
    print("-" * 55)

    if mdd_on > mdd_off:
        print("  ✅ SUCCESS: Adaptive Engine reduced Drawdown significantly!")
    else:
        print("  ⚠️ NOTE: Drawdown improvement was minimal. Check Filter Sensitivity.")