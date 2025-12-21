import pandas as pd
import yfinance as yf
import ccxt
import os

class DataLoader:
    def __init__(self):
        self.exchange = ccxt.binance()

    def fetch_stock_data(self, symbol: str, start: str, end: str = None) -> pd.DataFrame:
        print(f"[STOCK] {symbol} Collecting data...")
        df = yf.download(symbol, start=start, end=end, progress=False)

        if df.empty:
            print(f"⚠️ No data found for {symbol}")
            return pd.DataFrame()
        
        df = df.rename(columns={
            'Open': 'open', 'High': 'high', 'Low': 'low',
            'Close': 'close', 'Volume': 'volume'
        })

        df = df[['open', 'high', 'low', 'close', 'volume']]
        return df
    
    def fetch_crypto_data(self, symbol: str, timeframe: str = '1d', limit: int = 365) -> pd.DataFrame:
        print(f"[CRYPTO] {symbol} Collecting Data... ({timeframe})")

        if symbol not in self.exchange.load_markets():
            print(f"⚠️ {symbol} is not available on the exchange.")
            return pd.DataFrame()
        
        ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)

        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('date', inplace=True)
        df.drop(columns=['timestamp'], inplace=True)

        return df
    
    def save_to_csv(self, df: pd.DataFrame, file_name: str):
        save_path = f"data/raw/{file_name}.csv"
        
        os.makedirs("data/raw", exist_ok=True)

        df.to_csv(save_path)
        print(f"✅ Data saved to {save_path}")