import requests
import yfinance as yf
import pandas as pd
import numpy as np

def fetch_data(symbol, start, end):
    print(f"  [Data] Downloading {symbol}...")
    df = yf.download(symbol, start=start, end=end, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    return df

print("\n=======================================================")
print(" 🔬 COINTEGRATION TEST: Calculating Hedge Ratio (Beta)")
print("=======================================================")

start_date = "2023-01-01"
end_date = "2023-12-31"

ko = fetch_data("KO", start_date, end_date)["Close"].tolist()
pep = fetch_data("PEP", start_date, end_date)["Close"].tolist()

min_len = min(len(ko), len(pep))
ko = ko[:min_len]
pep = pep[:min_len]

log_x = np.log(ko)
log_y = np.log(pep)
slope, intercept = np.polyfit(log_x, log_y, 1)
print(f"\n  [Python Numpy] Beta: {slope:.4f}, Alpha: {intercept:.4f}")

import sys
import os
sys.path.append(os.path.abspath("build/src"))

try:
    import FinancialEngine as fe
    print("  [System] C++ Core Loaded Directly.")

    res = fe.Analytics.fit_linear_regression(log_x, log_y)

    print(f"  [C++ Engine]   Beta: {res.beta:.4f}, Alpha: {res.alpha:.4f}, R^2: {res.r_squared:.4f}")

    if abs(res.beta - slope) < 1e-5:
        print("\n  ✅ SUCCESS: C++ Calculation Matches Python Exactly!")
    else:
        print("\n  ❌ FAIL: Calculation Mismatch.")

except ImportError:
    print("\n  [Error] Could not load FinancialEngine module. Did you build it?")