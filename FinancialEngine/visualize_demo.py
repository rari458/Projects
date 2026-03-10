import sys
import os
import numpy as np
import matplotlib.pyplot as plt

sys.path.append(os.path.abspath("build/src"))

try:
    import FinancialEngine as fe
    print("[Success] FinancialEngine module loaded successfully.")
except ImportError as e:
    print(f"[Error] Could not import FinancialEngine: {e}")
    sys.exit(1)

def plot_profile():
    print("Running Simulation & Plotting...")

    spots = np.linspace(80, 120, 50)
    strike = 100.0
    r = 0.05
    d = 0.0
    vol = 0.2
    expiry = 1.0

    bs_prices = []
    tree_prices = []

    for S in spots:
        p1 = fe.black_scholes_call(S, strike, r, d, vol, expiry)
        bs_prices.append(p1)

        p2 = fe.binomial_tree_price(S, r, d, vol, expiry, 500, "put", strike, True)
        tree_prices.append(p2)

    plt.figure(figsize=(10, 6))

    plt.plot(spots, bs_prices, label='European Call (Black-Scholes)', color='blue', linewidth=2)

    plt.plot(spots, tree_prices, label='American Put (Binomial Tree)', color='red', linestyle='--', linewidth=2)
    
    plt.title(f"Financial Engine Pricing Profile (K={strike}, Vol={vol*100}%)")
    plt.xlabel("Spot Price (Underlying Asset)")
    plt.ylabel("Option Price")
    plt.axvline(x=strike, color='gray', linestyle=':', alpha=0.5, label='Strike Price')
    plt.legend()
    plt.grid(True, alpha=0.3)

    output_file = "option_valuation_chart.png"
    plt.savefig(output_file)
    print(f"\n[Done] Chart saved to '{output_file}'")

if __name__ == "__main__":
    plot_profile()