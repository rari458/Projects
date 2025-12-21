import ccxt
import pandas as pd
import time
import datetime
from src.strategy_bb import BBANDS
from src.notifier import Notifier # <--- NEW: Import Notifier

class PaperTradingBot:
    def __init__(self, symbol='BTC/USDT', timeframe='1m', initial_balance=10000):
        # 1. Initialize Notifier
        self.notifier = Notifier()

        self.exchange = ccxt.binance()
        self.symbol = symbol
        self.timeframe = timeframe
        self.balance_usdt = initial_balance
        self.balance_btc = 0
        self.position = None

        self.n_lookback = 30
        self.n_std = 2.0

        start_msg = f"🤖 [START] Bot started for {symbol} ({timeframe})\n💰 Balance: ${self.balance_usdt:,.2f}"
        print(start_msg)
        self.notifier.send(start_msg) # <--- Send to Telegram

    def fetch_data(self):
        try:
            ohlcv = self.exchange.fetch_ohlcv(self.symbol, self.timeframe, limit=50)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['close'] = pd.to_numeric(df['close'])
            return df
        except Exception as e:
            print(f"[ERROR] Fetch data failed: {e}")
            return pd.DataFrame()
        
    def get_current_price(self):
        try:
            ticker = self.exchange.fetch_ticker(self.symbol)
            return ticker['last']
        except Exception as e:
            print(f"[ERROR] Fetch ticker failed: {e}")
            return None
        
    def run(self):
        print(f"[BOT] Trading loop started...")

        while True:
            try:
                # Data & Indicators
                df = self.fetch_data()
                if df.empty:
                    time.sleep(10)
                    continue

                closes = df['close'].values
                bbl, bbm, bbu = BBANDS(closes, self.n_lookback, self.n_std)
                current_bbl, current_bbu = bbl[-1], bbu[-1]

                # Real-time Price
                current_price = self.get_current_price()
                if current_price is None:
                    time.sleep(10)
                    continue

                # Log Status (Console only, to avoid spamming Telegram)
                now = datetime.datetime.now().strftime("%H:%M:%S")
                print(f"[{now}] Now: {current_price:.2f} | LowBand: {current_bbl:.2f} | HighBand: {current_bbu:.2f}")

                # --- BUY LOGIC ---
                if self.position is None and current_price < current_bbl:
                    amount_to_buy = (self.balance_usdt / current_price) * 0.99
                    self.balance_btc = amount_to_buy
                    self.balance_usdt = 0
                    self.position = 'LONG'

                    msg = (f"🚀 [BUY] Signal!\n"
                           f"Price: ${current_price:,.2f}\n"
                           f"Amt: {amount_to_buy:.4f} BTC")
                    print(msg)
                    self.notifier.send(msg) # <--- Alert!

                # --- SELL LOGIC ---
                elif self.position == 'LONG' and current_price > current_bbu:
                    revenue = self.balance_btc * current_price
                    profit = revenue - (self.balance_btc * float(df['close'].iloc[-2])) # Approx profit
                    self.balance_usdt = revenue
                    self.balance_btc = 0
                    self.position = None

                    msg = (f"💰 [SELL] Profit Taken!\n"
                           f"Price: ${current_price:,.2f}\n"
                           f"Balance: ${self.balance_usdt:,.2f}")
                    print(msg)
                    self.notifier.send(msg) # <--- Alert!

                time.sleep(60)

            except KeyboardInterrupt:
                print("Stopping...")
                self.notifier.send("🛑 [STOP] Bot stopped manually.")
                break
            except Exception as e:
                err_msg = f"⚠️ Error: {e}"
                print(err_msg)
                self.notifier.send(err_msg) # <--- Error Alert
                time.sleep(10)