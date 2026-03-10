import requests
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

def fetch_data(symbol, start, end):
    print(f"  [Data] Downloading {symbol}...")
    df = yf.download(symbol, start=start, end=end, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    return df

def test_pairs_trading():
    print("\n=======================================================")
    print(" ⚔️  KALMAN FILTER PAIRS TRADING TEST (KO vs PEP)  ⚔️")
    print("=======================================================")

    start_date = "2022-01-01"
    end_date = "2022-12-31"

    ko = fetch_data("KO", start_date, end_date)
    pep = fetch_data("PEP", start_date, end_date)

    common_index = ko.index.intersection(pep.index)
    ko = ko.loc[common_index]
    pep = pep.loc[common_index]

    print(f"  > Data synchronized: {len(common_index)} days")

    payload = {
        "initial_capital": 20000.0,
        "strategy": "PAIRS",
        "leverage": 1.0,
        "max_drawdown_limit": 0.10,
        "pairs_window": 21,
        "pairs_threshold": 2.39,
        
        "assets": {
            "KO": {
                "opens": ko["Open"].tolist(),
                "highs": ko["High"].tolist(),
                "lows": ko["Low"].tolist(),
                "closes": ko["Close"].tolist()
            },
            "PEP": {
                "opens": pep["Open"].tolist(),
                "highs": pep["High"].tolist(),
                "lows": pep["Low"].tolist(),
                "closes": pep["Close"].tolist()
            }
        }
    }

    try:
        resp = requests.post("http://localhost:8000/api/backtest", json=payload)

        if resp.status_code == 200:
            res = resp.json()
            print("\n  [Result Analysis]")
            print(f"  > Final Equity:  ${res['final_equity']:,.2f}")
            print(f"  > Return:        {res['return_pct']:.2f}%")
            print(f"  > Max Drawdown:  {res['max_drawdown']:.2f}%")
            print(f"  > Trades:        {res['total_trades']}")

            if res['total_trades'] > 0:
                print("\n  [Recent Trades]")
                for t in res['trade_history'][-5:]:
                    print(f"    - [{t['symbol']}] {t['side']} {t['qty']:.4f} units @ ${t['price']:.2f}")

            equity_curve = res.get('equity_history', [])
            if equity_curve:
                plt.figure(figsize=(12, 6))
                plt.plot(equity_curve, label='Strategy Equity', color='blue', linewidth=1.5)

                plt.axhline(y=20000.0, color='r', linestyle='--', label='Initial Capital ($20,000)')

                plt.title(f"Kalman Filter Strategy Performance (2022 Bear Market)\nReturn: {res['return_pct']:.2f}% | MDD: {res['max_drawdown']:.2f}%")
                plt.xlabel("Trading Days")
                plt.ylabel("Equity ($)")
                plt.legend()
                plt.grid(True, which='both', linestyle='--', alpha=0.6)
                plt.tight_layout()

                filename = "pairs_trading_result.png"
                plt.savefig(filename)
                print(f"\n  [Graph Saved] '{filename}' saved successfully.")

        else:
            print(f"  [Error] {resp.status_code}: {resp.text}")

    except Exception as e:
        print(f"  [Connection Error] Is the server running? {e}")

if __name__ == "__main__":
    test_pairs_trading()