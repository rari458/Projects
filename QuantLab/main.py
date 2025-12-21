from src.data_loader import DataLoader
from src.strategy_bb import BollingerMeanReversion
from backtesting import Backtest
import pandas as pd
import numpy as np # Needed for range generation

def main():
    loader = DataLoader()

    print("\n" + "="*50)
    print(" >>> OPTIMIZATION: Bollinger Band Strategy")
    print("="*50)

    # Fetch Data
    df = loader.fetch_crypto_data("BTC/USDT", timeframe='1d', limit=730)
    if df.empty: return

    # Rename for Backtesting
    mapping = {
        'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'
    }
    df = df.rename(columns=mapping)

    # Setup Backtest
    bt = Backtest(df, BollingerMeanReversion, cash=1000000, commission=0.002, exclusive_orders=True)

    # Run Optimization
    print("Running optimization (Scanning parameters)...")

    # We define the search space
    stats = bt.optimize(
        n_lookback=range(10, 50, 5),        # Test windows: 10, 15... 45
        n_std=[1.5, 1.8, 2.0, 2.2, 2.5],    # Test band widths
        maximize='Return [%]'               # Goal: Maximize Profit 
    )

    # Results
    print("\n" + "-"*30)
    print("      OPTIMIZATION RESULTS      ")
    print("-"*-30)
    print(stats)
    print("-"*-30)

    print(f"Best Parameters found:")
    print(f" - Lookback Period: {stats._strategy.n_lookback}")
    print(f" - Std Deviation: {stats._strategy.n_std}")
    print(f" - Final Return: {stats['Return [%]']:.2f}%")
    print(f" - Buy & Hold Return: {stats['Buy & Hold Return [%]']:.2f}%")
    print(f" - Win Rate: {stats['Win Rate [%]']:.2f}%")

    # Save Plot
    output_file = 'data/bb_optimized_result.html'
    print(f"Saving plot to '{output_file}'...")
    bt.plot(filename=output_file, open_browser=False)

if __name__ == "__main__":
    main()