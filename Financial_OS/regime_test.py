import requests
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

def fetch_prices(symbol, start, end):
    print(f"  [Data] Downloading {symbol} ({start} ~ {end})...")
    df = yf.download(symbol, start=start, end=end, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    return df["Close"].tolist()

def check_regime(scenario_name, prices):
    payload = {"prices": prices, "window_size": 20}
    try:
        resp = requests.post("http://localhost:8000/api/regime", json=payload)
        if resp.status_code == 200:
            res = resp.json()
            print(f"\n  🔍 Scenario: {scenario_name}")
            print(f"  > Market State:  {res['state_name'].upper()} (ID: {res['state_id']})")
            print(f"  > Volatility:    {res['current_volatility']:.4f}")
            print(f"  > Trend:         {res['current_trend']:.4f}")
            return res
        else:
            print(f"  [Error] {resp.text}")
    except Exception as e:
        print(f"  [Connection Error] {e}")

if __name__ == "__main__":
    print("=======================================================")
    print(" 🌦️  MARKET REGIME DETECTION TEST (S&P 500)")
    print("=======================================================")

    prices_2022 = fetch_prices("SPY", "2021-01-01", "2022-9-30")
    check_regime("2022 Bear Market (Context Added)", prices_2022)

    prices_2023 = fetch_prices("SPY", "2023-01-01", "2023-12-31")
    check_regime("2023 Bull Market (Rally)", prices_2023)

    prices_now = fetch_prices("SPY", "2024-01-01", "2024-12-31")
    check_regime("2024 Current Market", prices_now)