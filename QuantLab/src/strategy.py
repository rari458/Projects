import pandas as pd
from backtesting import Strategy
from backtesting.lib import crossover

def SMA(values, n):
    """
    Helper function to calculate Simple Moving Average.
    :param values: Price series (e.g., Close prices)
    :param n: Window size (e.g., 10, 20)
    :return: Pandas Series of SMA
    """
    return pd.Series(values).rolling(n).mean()

class SmaCross(Strategy):
    # Define parameters (can be optimized later)
    n1 = 10 # Short-term MA window
    n2 = 20 # Long-term MA window

    def init(self):
        """
        Initialize indicators.
        Run once before the backtest starts.
        """
        # Calculate SMA using the helper function
        # self.data.Close represents the close price array
        self.sma1 = self.I(SMA, self.data.Close, self.n1)
        self.sma2 = self.I(SMA, self.data.Close, self.n2)

    def next(self):
        """
        Executed for every new data candle.
        This is where the trading logic resides.
        """

        # Logic: Buy if SMA1 crosses above SMA2
        if crossover(self.sma1, self.sma2):
            # Close any existing short position (if any) and buy
            # size=0.95 means "Invest 95% of available cash"
            self.buy(size=0.95)

        # Logic: Sell if SMA1 crosses below SMA2
        elif crossover(self.sma2, self.sma1):
            # Close long positions
            self.position.close()