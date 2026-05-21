import sys
import os

sys.path.append(os.path.abspath("build/src"))

try:
    import FinancialEngine as fe
    print("\n[Success] FinancialEngine Module Imported!\n")
except ImportError as e:
    print(f"\n[Error] Failed to import FinancialEngine: {e}")
    sys.exit(1)

spot = 100.0
strike = 100.0
rate = 0.05
div = 0.0
vol = 0.2
expiry = 1.0

bs_price = fe.black_scholes_call(spot, strike, rate, div, vol, expiry)
print(f"1. Black-Scholes Call Price (C++): {bs_price:.5f}")

steps = 500
is_american = True
tree_price = fe.binomial_tree_price(spot, rate, div, vol, expiry, steps, "put", strike, is_american)

print(f"2. Binomial Tree American Put (C++): {tree_price:.5f}")

import time
start = time.time()
for _ in range(1000):
    fe.black_scholes_call(spot, strike, rate, div, vol, expiry)
end = time.time()
print(f"3. Performance: 1000 calculations took {end - start:.5f} sec")