import pandas as pd
import matplotlib.pyplot as plt
import os

class Visualizer:
    def __init__(self):
        # Set the style for the plots
        plt.style.use('bmh')
    
    def plot_price_and_returns(self, df: pd.DataFrame, title: str = "Asset Performance"):
        """
        Plots the Close Price and Cumulative Return on two separate subplots.
        """
        if df.empty:
            print("Error: DataFrame is empty. Nothing to plot.")
            return
        
        print(f"Visualizing: Generating plot for {title}...")

        # Create a figure with 2 subplots (nrows=2, ncols=1)
        fig, (ax1, ax2) = plt.subplots(nrows=2, ncols=1, figsize=(12, 8), sharex=True)

        # Plot 1: Close Price
        ax1.plot(df.index, df['close'], color='blue', label='Close Price')
        ax1.set_title(f"{title} - Price History")
        ax1.set_ylabel("Price")
        ax1.legend(loc="upper left")
        ax1.grid(True)

        # Plot 2: Cumulative Return (Percentage)
        # Convert to percentage (e.g., 0.15 -> 15%)
        cum_ret_pct = df['cumulative_return'] * 100

        ax2.plot(df.index, cum_ret_pct, color='green', linestyle='--', label='Cumulative Return %')

        # Add a horizontal line at 0% for reference
        ax2.axhline(0, color='red', linewidth=1, linestyle='-')

        ax2.set_title("Cumulative Return (%)")
        ax2.set_ylabel("Return (%)")
        ax2.set_xlabel("Date")
        ax2.legend(loc="upper left")
        ax2.grid(True)

        # Adjust layout to prevent overlap
        plt.tight_layout()

        # Save the plot
        save_dir = "data/plots"
        os.makedirs(save_dir, exist_ok=True)
        save_path = f"{save_dir}/{title}_performance.png"
        plt.savefig(save_path)

        print(f" - Plot saved to: {save_path}")

        # Show the plot
        plt.show()