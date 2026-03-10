# live_stream.py

import websocket
import json
import sys
import os
import time

# Append C++ Core Directory
sys.path.append(os.path.abspath('./build/src'))
try:
    import FinancialEngine
except ImportError:
    print("[Error] Failed to import FinancialEngine C++ Core.")
    sys.exit(1)

# Initialize C++ Engine globally
initial_capital = 100000.0
strategy_name = "BB"
ticker = "BTC"

print("==================================================")
print("  Aladdin-Killer: LIVE Market Nervous System      ")
print("==================================================")
print(f"-> Booting Native C++ Engine with Strategy: {strategy_name}")

engine = FinancialEngine.Backtester(initial_capital, strategy_name, 1.0)
engine.set_regime_filter(False, 252)
tick_count = 0

def on_message(ws, message):
    global tick_count
    data = json.loads(message)

    # Parse Binance Aggregate Trade Data
    # 'p': Pirce, 'q': Quantity, 'T': Timestamp
    price = float(data['p'])
    volume = float(data['q'])
    timestamp = float(data['T']) / 1000.0 # Convert ms to senconds

    # Inject real-time tick into C++ Core (Tick data: O=H=L=C=Price)
    engine.on_market_data(ticker, timestamp, price, price, price, price)

    tick_count += 1

    # Console Update (Print every 10 ticks to prevent console IO bottleneck)
    if tick_count % 10 == 0:
        equity = engine.get_total_equity()
        trades = len(engine.get_trade_history())
        inventory = engine.get_holdings(ticker)
        print(f"[Live Tick {tick_count:>4} {ticker} Price: ${price:.2f} | Inventory: {inventory:.4f} | Trades: {trades} | C++ Equity: ${equity:.2f}]")

def on_error(ws, error):
    print(f"\n[WebSocket Error] {error}")

def on_close(ws, close_status_code, close_msg):
    print("\n==================================================")
    print("  Connection Closed. Final Engine State:          ")
    print("==================================================")
    print(f"Final Equity: ${engine.get_total_equity():.2f}")
    print(f"Total Trades: {len(engine.get_trade_history())}")
    print("Shutting down FinancialOS Live System.")

def on_open(ws):
    print("-> Connected to Binance Live Websocket (BTC/USDT AggTrades).")
    print("-> Streaming live ticks to C++ Engine. Press Ctrl+C to stop...\n")

if __name__ == "__main__":
    # Binance Live Websocket Endpoint (BTC/USDT Aggregate Trades)
    socket_url = "wss://stream.binance.com:9443/ws/btcusdt@aggTrade"

    ws = websocket.WebSocketApp(
        socket_url,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )

    try:
        ws.run_forever()
    except KeyboardInterrupt:
        print("\n -> Manual interrupt received.")
        ws.close()