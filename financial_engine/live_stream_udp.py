# live_stream_udp.py

import socket
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

def main():
    print("==================================================")
    print("  Aladdin-Killer: L2 Microstructure Trinity       ")
    print("==================================================")

    # Initialize Engine (Using L3_EXECUTION Strategy)
    initial_capital = 100000.0
    strategy_name = "L3_EXECUTION"
    ticker = "BTC"

    print(f"-> Booting Native C++ Engine with Strategy: {strategy_name}")
    engine = FinancialEngine.Backtester(initial_capital, strategy_name, 1.0)
    engine.set_regime_filter(False, 252)

    UDP_IP = "127.0.0.1"
    UDP_PORT = 9999
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))

    print(f"-> [Python Bridge] Listening for Rust L2 payloads on port {UDP_PORT}...")

    tick_count = 0

    try:
        while True:
            data, _ = sock.recvfrom(1024)
            payload = data.decode('utf-8').split(',')

            if len(payload) == 3:
                best_bid = float(payload[0])
                best_ask = float(payload[1])
                obi = float(payload[2])
                current_time = time.time()

                # 1. Update standard price (Mid Price)
                mid_price = (best_bid + best_ask) / 2.0
                engine.on_market_data(ticker, current_time, mid_price, mid_price, mid_price, mid_price)

                #2. Inject Microstructure Event directly into C++ core
                msg = FinancialEngine.MicrostructureMessage(
                    current_time, "BINANCE_L2", best_bid, best_ask, False
                )
                engine.send_microstructure_msg(msg)

                tick_count += 1
                if tick_count % 20 == 0:
                    print(f"[Core Sync {tick_count:>4}] Bid: {best_bid:.2f} | Ask: {best_ask:.2f} | OBI: {obi:+.4f} | Spread: {best_ask-best_bid:.2f}")

                    if obi > 0.6:
                        print(f"   >>> [Rust Signal Alert] Extreme Buy Pressure Detected (OBI={obi:+.4f}). Engine preparing execution.")
                    elif obi < -0.6:
                        print(f"   >>> [Rust Signal Alert] Extreme Sell Wall Detected (OBI={obi:+.4f}). Engine preparing defense.")

    except KeyboardInterrupt:
        print("\nShutting down FinancialOS Live System.")

if __name__ == "__main__":
    main()