import pandas as pd
import numpy as np
from backtesting import Strategy

# --- FIX: Manual Bollinger Bands Calculation ---
def BBANDS(data, n_lookback, n_std):
    """
    Calculates Bollinger Bands manually using pandas rolling functions.
    Returns: Lower Band, Middle Band, Upper Band (as numpy arrays)
    """
    # 1. Convert numpy array to pandas Series for rolling calculation
    series = pd.Series(data)

    # 2. Calculate Middle Band (Simple Moving Average)
    mid = series.rolling(window=n_lookback).mean()

    # 3. Calculate Standard Deviation
    std = series.rolling(window=n_lookback).std()

    # 4. Calculate Upper & Lower Bands
    upper = mid + (std * n_std)
    lower = mid - (std * n_std)

    # 5. Fill NaNs with 0 (Backtesting engine handles 0 better than NaN)
    # and convert back to numpy array
    return lower.fillna(0).to_numpy(), mid.fillna(0).to_numpy(), upper.fillna(0).to_numpy()

class BollingerMeanReversion(Strategy):
    # Parameters to optimize
    n_lookback = 20    # Period
    n_std = 2.0        # Standard Deviation

    def init(self):
        # Use the manual function defined above
        self.bbl, self.bbm, self.bbu = self.I(BBANDS, self.data.Close, self.n_lookback, self.n_std)

    def next(self):
        price = self.data.Close[-1]

        # Buy Condition: Price falls below Lower Band (Oversold)
        # Avoid buying if the band is 0 (initial calculation period)
        if self.bbl[-1] > 0 and price < self.bbl[-1]:
            if not self.position:
                self.buy()

        # Sell Condition: Price hits the Upper Band
        elif self.bbu[-1] > 0 and price > self.bbu[-1]:
            if self.position:
                self.position.close()