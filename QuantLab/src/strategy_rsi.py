import pandas as pd
from backtesting import Strategy
from backtesting.lib import crossover

def SMA(values, n):
    """Helper to calculate SMA"""
    return pd.Series(values).rolling(n).mean()

class SmaRsiStrategy(Strategy):
    # Parameters to optimize
    n1 = 10         # Short MA
    n2 = 20         # Long MA
    rsi_limit = 70  # RSI Threshold (Do not buy if RSI is above this)

    def init(self):
        # 1. Calculate SMAs
        self.sma1 = self.I(SMA, self.data.Close, self.n1)
        self.sma2 = self.I(SMA, self.data.Close, self.n2)

        # 2. Import RSI from Data
        # We use a lambda function to just return the pre-calculated 'RSI' column
        # allowing it to be plotted on the chart.
        self.rsi = self.I(lambda x: x, self.data.RSI)

    def next(self):
        # Buy Condition:
        # 1. SMA Golden Cross (Short > Long)
        # 2. RSI is NOT Overbought (RSI < rsi_limit)
        if crossover(self.sma1, self.sma2) and self.rsi[-1] < self.rsi_limit:
            self.buy()

        # Sell Condition:
        # SMA Death Cross (Short < Long)
        elif crossover(self.sma2, self.sma1):
            self.position.close()