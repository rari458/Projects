import sys
import os

sys.path.append(os.path.abspath("build/src"))

try:
    import FinancialEngine as fe
except ImportError as e:
    print(f"[Error] Failed to load C++ Core: {e}")
    sys.exit(1)

def run_greeks_test():
    print("\n=======================================================")
    print(" ⚡ DERIVATIVES ENGINE: GREEKS CALCULATION TEST")
    print("=======================================================")

    spot = 100.0
    strike = 100.0
    r = 0.05
    d = 0.0
    vol = 0.20
    expiry = 1.0

    print(f"  [Input] Spot: {spot}, Strike: {strike}, Vol: {vol*100}%, Expiry: {expiry}Y\n")

    is_call = True
    call_greeks = fe.calculate_greeks(spot, strike, r, d, vol, expiry, is_call)

    is_call = False
    put_greeks = fe.calculate_greeks(spot, strike, r, d, vol, expiry, is_call)

    print("  [Call Option Greeks]")
    print(f"  > Delta: {call_greeks.delta:>8.4f}  (Expected ~ 0.5 to 0.6 ATM)")
    print(f"  > Gamma: {call_greeks.gamma:>8.4f}")
    print(f"  > Theta: {call_greeks.theta:>8.4f}")
    print(f"  > Vega:  {call_greeks.vega:>8.4f}")
    print(f"  > Rho:   {call_greeks.rho:>8.4f}\n")

    print("  [Put Option Greeks]")
    print(f"  > Delta: {put_greeks.delta:>8.4f}  (Expected ~ -0.4 to 0.5 ATM)")
    print(f"  > Gamma: {put_greeks.gamma:>8.4f}  (Should match Call Gamma)")
    print(f"  > Theta: {put_greeks.theta:>8.4f}")
    print(f"  > Vega:  {put_greeks.vega:>8.4f}  (Should match Call Vega)")
    print(f"  > Rho:   {put_greeks.rho:>8.4f}\n")

if __name__ == "__main__":
    run_greeks_test()