import requests
import yfinance as yf
import pandas as pd
import time

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META"]

def fetch_data(symbol, start, end):
    print(f"  [Data] Downloading {symbol}...")
    try:
        df = yf.download(symbol, start=start, end=end, progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        return df
    except Exception as e:
        print(f"  [Error] Failed to download {symbol}: {e}")
        return None

def run_universe_mining():
    print("\n=======================================================")
    print(f" 🛰️  UNIVERSE MINING: Scanning {len(TICKERS)} Tech Giants")
    print("=======================================================")

    start_date = "2023-01-01"
    end_date = "2023-12-31"

    assets_payload = {}
    valid_tickers = []

    for ticker in TICKERS:
        df = fetch_data(ticker, start_date, end_date)
        if df is not None and len(df) > 50:
            assets_payload[ticker] = {
                "opens": df["Open"].tolist(),
                "highs": df["High"].tolist(),
                "lows": df["Low"].tolist(),
                "closes": df["Close"].tolist()
            }
            valid_tickers.append(ticker)

    print(f"  > Data preparation complete. Sending to C++ Engine...")

    payload = {"assets": assets_payload}

    start_time = time.time()
    try:
        resp = requests.post("http://localhost:8000/api/scan", json=payload)

        if resp.status_code == 200:
            res = resp.json()
            top_pairs = res.get("top_pairs", [])
            best = top_pairs[0] if top_pairs else None
            elapsed = (time.time() - start_time) * 1000

            print("\n  [Scan Result]")
            print(f"  > Scanned Assets: {res['scanned_count']}")
            print(f"  > Time Elapsed:   {elapsed:.2f} ms")
            print("-" * 65)
            print(f"  {'Pair':<15} | {'Corr':<8} | {'Beta':<8} | {'R^2':<8}")
            print("-" * 65)

            for p in res["top_pairs"]:
                pair_name = f"{p['asset_a']}-{p['asset_b']}"
                print(f"  {pair_name:<15} | {p['correlation']:.4f}   | {p['beta']:.4f}   | {p['r_squared']:.4f}")
            print("-" * 65)

            if best['correlation'] > 0.8:
                print("  ✅ High Correlation! Ready for Pairs Trading.")
            else:
                print("  ⚠️ Correlation is weak. Maybe try other sectors?")

        else:
            print(f"  [Error] {resp.status_code}: {resp.text}")

    except Exception as e:
        print(f"  [Connection Error] {e}")

if __name__ == "__main__":
    run_universe_mining()