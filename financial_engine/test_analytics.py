import sys
import os
import numpy as np
import matplotlib.pyplot as plt

sys.path.append(os.path.abspath("build/src"))
import FinancialEngine as fe

def run_analytics_test():
    print("=== Financial Engine: Analytics Module Test ===\n")

    np.random.seed(42)
    S0 = 100
    mu = 0.1
    sigma = 0.2
    dt = 1/252
    days = 1000

    prices = [S0]
    for _ in range(days):
        drift = (mu - 0.5 * sigma**2) * dt
        shock = sigma * np.sqrt(dt) * np.random.normal()
        prices.append(prices[-1] * np.exp(drift + shock))

    print(f"Generated {len(prices)} days of price data.")

    cpp_returns = fe.Analytics.calculate_log_returns(prices)
    cpp_vol = fe.Analytics.calculate_volatility(cpp_returns)
    cpp_var_95 = fe.Analytics.calculate_var(cpp_returns, 0.95)
    cpp_es_95 = fe.Analytics.calculate_es(cpp_returns, 0.95)

    np_prices = np.array(prices)
    np_returns = np.log(np_prices[1:] / np_prices[:-1])
    np_vol = np.std(np_returns)

    np_var_95 = -np.percentile(np_returns, 5)

    tail_loss = np_returns[np_returns <= -np_var_95]
    np_es_95 = -np.mean(tail_loss)

    print(f"\n[Performance & Accuracy Check]")
    print(f"{'Metric':<20} | {'C++ Engine':<15} | {'NumPy (Ref)':<15} | {'Diff'}")
    print("-" * 65)
    print(f"{'Volatility':<20} | {cpp_vol:.8f}      | {np_vol:.8f}      | {abs(cpp_vol - np_vol):.2e}")
    print(f"{'VaR (95%)':<20} | {cpp_var_95:.8f}      | {np_var_95:.8f}      | {abs(cpp_var_95 - np_var_95):.2e}")
    print(f"{'ES (95%)':<20}  | {cpp_es_95:.8f}      | {np_es_95:.8f}      | {abs(cpp_es_95 - np_es_95):.2e}")

    plt.figure(figsize=(10, 6))
    plt.hist(np_returns, bins=50, alpha=0.6, color='blue', label='Daily Returns')
    plt.axvline(-cpp_var_95, color='red', linestyle='--', linewidth=2, label=f'VaR 95%: {-cpp_var_95:.4f}')
    plt.axvline(-cpp_es_95, color='orange', linestyle='--', linewidth=2, label=f'ES 95%: {-cpp_es_95:.4f}')
    plt.title("Return Distribution with Risk Metrics (Powered by C++ Core)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig("risk_analysis.png")
    print(f"\n[Visualization] Saved risk distribution chart to 'risk_analysis.png'")

if __name__ == "__main__":
    run_analytics_test()