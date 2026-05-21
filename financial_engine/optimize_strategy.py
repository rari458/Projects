import requests
import yfinance as yf
import pandas as pd
import numpy as np
import time
import itertools

BASE_URL = "http://localhost:8000/api"

def fetch_price_history(symbol, period="2y"):
    ticker = yf.ticker(symbol)
    hist = ticker.history(period=period)
    return hist['Close'].tolist()

def run_grid_search(symbol="NVDA"):
    print(f"\n=== [Hyperparameter Tuning] Finding Best EMA Pairs for {symbol} ===")

    prices = fetch_price_history(symbol)
    if not prices:
        return

    shorts = range(5, 55, 5)
    longs = range(20, 210, 10)

    best_return = -999.0
    best_params = (0, 0)

    total_combinations = len(list(itertools.product(shorts, longs)))
    print(f"  > Scanning {total_combinations} parameter combinations...")

    start_time = time.time()

    print("\n[System Alert] Currently the C++ engine is fixed at 20/50 EMA.")
    print("Rather than simply tuning parameters, we need to ‘upgrade the strategy itself.’")

if __name__ == "__main__":
    run_grid_search()