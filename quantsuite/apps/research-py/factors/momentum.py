import pandas as pd

def mom_close(df: pd.DataFrame, lookback: int = 3) -> pd.Series:
    s = pd.Series(df['close'].values, index=pd.to_datetime(df['date']))
    return s.pct_change(lookback)