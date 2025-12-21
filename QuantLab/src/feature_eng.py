import pandas as pd
import pandas_ta as ta

class FeatureEngineer:
    def __init__(self):
        pass

    def add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Adds technical indicators (RSI, Bollinger Bands) using pandas_ta.
        """
        if df.empty:
            print("Error: DataFrame is empty.")
            return df
        
        df = df.copy()

        # 1. RSI
        df['RSI'] = df.ta.rsi(length=14)

        # 2. Bollinger Bands
        # length=20, std=2 (Standard Deviation)
        # It returns 3 columns: BBL (Lower), BBM (Middle), BBU (Upper)
        bb = df.ta.bbands(length=20, std=2)

        # Append these columns to our main DataFrame
        # Column names might vary by version, usually: BBL_20_2.0, BBM_20_2.0, BBU_20_2.0
        # We reanme them for easier access
        df = pd.concat([df, bb], axis=1)

        # Rename columns dynamically to standard names 'BBL', 'BBM', 'BBU'
        # The library produces names like 'BBL_20_2.0', so we find them by prefix
        cols = df.columns
        bbl_col = [c for c in cols if c.startswith('BBL')][0]
        bbm_col = [c for c in cols if c.startswith('BBM')][0]
        bbu_col = [c for c in cols if c.startswith('BBU')][0]

        df.rename(columns={bbl_col: 'BBL', bbm_col: 'BBM', bbu_col: 'BBU'}, inplace=True)

        df.dropna(inplace=True)

        print(f"Feature Engineering: Added RSI and Bollinger Bands. (Rows: {len(df)})")
        return df