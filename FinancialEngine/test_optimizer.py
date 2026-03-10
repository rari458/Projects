import sys
import os
import time
import numpy as np
import matplotlib.pyplot as plt

sys.path.append(os.path.abspath("build/src"))
import FinancialEngine as fe

def generate_synthetic_data(n_days=252):
    np.random.seed(42)
    assets = ['AAPL', 'MSFT', 'GOOG', 'AMZN', 'TSLA']

    mus = [0.15, 0.12, 0.14, 0.13, 0.25]
    vols = [0.20, 0.18, 0.22, 0.25, 0.40]

    data = {}
    dt = 1/252

    print(f"[DataGen] Generating {n_days} days of data for {len(assets)} assets...")

    for i, symbol in enumerate(assets):
        mu, sigma = mus[i], vols[i]
        returns = np.random.normal((mu - 0.5 * sigma**2) * dt, sigma * np.sqrt(dt), n_days)
        data[symbol] = returns.tolist()

    return assets, data

def run_optimization_test():
    print("=== Financial Engine: Portfolio Optimizer Test (C++ Core) ===\n")

    assets, data = generate_synthetic_data()

    opt = fe.Optimizer()
    for symbol in assets:
        opt.add_asset(symbol, data[symbol])

    num_sims = 100_00
    print(f"\n[Engine] Running {num_sims:,} Monte Carlo simulations in C++...")

    start_time = time.time()

    result = opt.optimize_sharpe_ratio(num_sims, 0.02)

    end_time = time.time()
    elapsed = end_time - start_time

    print(f"[Done] Optimization completed in {elapsed:.6f} seconds.")
    print(f"       Speed: {num_sims / elapsed:,.0f} simulations/sec\n")

    print("-" * 50)
    print(f"Optimal Portfolio (Max Sharpe: {result.sharpe_ratio:.4f})")
    print("-" * 50)
    print(f"Expected Return:     {result.portfolio_return * 100:.2f}%")
    print(f"Expected Volatility: {result.portfolio_volatility * 100:.2f}%")
    print("-" * 50)
    print("Asset Allocation:")

    sorted_alloc = sorted(zip(assets, result.optimal_weights), key=lambda x: x[1], reverse=True)

    for symbol, weight in sorted_alloc:
        print(f"  {symbol:<5}: {weight*100:6.2f}%")

    labels = [x[0] for x in sorted_alloc]
    sizes = [x[1] for x in sorted_alloc]

    plt.figure(figsize=(8, 8))
    plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140, colors=plt.cm.Paired.colors)
    plt.title(f"Optimal Asset Allocation (Max Sharpe)\nReturn: {result.portfolio_return:.1%} | Vol: {result.portfolio_volatility:.1%}")

    output_file = "portfolio_allocation.png"
    plt.savefig(output_file)
    print(f"\n[Visualization] Allocation chart saved to '{output_file}'")

if __name__ == "__main__":
    run_optimization_test()