import requests
import numpy as np

BASE_URL = "http://localhost:8000/api"

def test_backtest():
    print("\n[Test 1] Backtesting API...")

    prices = [100 + 10 * np.sin(i * 0.1) for i in range(200)]

    payload = {
        "initial_capital": 10000.0,
        "prices": prices
    }

    resp = requests.post(f"{BASE_URL}/backtest", json=payload)
    if resp.status_code == 200:
        data = resp.json()
        print(f"  > Success! Return: {data['return_pct']:.2f}%")
        print(f"  > Trades Executed: {data['total_trades']}")
    else:
        print(f"  > Failed: {resp.text}")

def test_optimizer():
    print("\n[Test 2] Optimizer API...")

    np.random.seed(42)
    assets = {
        "AAPL": np.random.normal(0.001, 0.02, 100).tolist(),
        "TSLA": np.random.normal(0.002, 0.04, 100).tolist(),
        "GOOG": np.random.normal(0.001, 0.015, 100).tolist()
    }

    payload = {
        "assets": assets,
        "risk_free_rate": 0.02,
        "num_simulations": 50000
    }

    resp = requests.post(f"{BASE_URL}/optimize", json=payload)
    if resp.status_code == 200:
        data = resp.json()
        print(f"  > Success! Max Sharpe: {data['max_sharpe']:.4f}")
        print(f"  > Allocation: {data['allocation']}")
    else:
        print(f"  > Failed: {resp.text}")

if __name__ == "__main__":
    try:
        test_backtest()
        test_optimizer()
    except requests.exceptions.ConnectionError:
        print("[Error] Server is not running. Please run 'python3 server/main.py' first.")