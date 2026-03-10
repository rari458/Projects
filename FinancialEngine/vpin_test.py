import sys
import os
import random

sys.path.append(os.path.abspath("build/src"))

try:
    import FinancialEngine as fe
except ImportError as e:
    print(f"[Error] Failed to load C++ Core: {e}")
    sys.exit(1)

def simulate_trades(book, start_time, num_trades, trade_size, buy_prob):
    timestamp = start_time
    for i in range(num_trades):
        is_buy = random.random() < buy_prob
        qty = trade_size * random.uniform(0.8, 1.2)
        price = 100.0 if is_buy else 99.9

        book.record_trade(price, qty, is_buy, timestamp)
        timestamp += 0.001

def run_vpin_test():
    print("\n=======================================================")
    print(" 🧠 L2 MICROSTRUCTURE: VPIN TOXIC FLOW DETECTION")
    print("=======================================================")

    book = fe.OrderBook("SPY")

    BUCKET_SIZE = 1000.0
    NUM_BUCKETS = 10

    print("  [Phase 1] Normal Market Conditions (Balanced Trade Flow)")
    simulate_trades(book, 1000.0, num_trades=150, trade_size=100.0, buy_prob=0.50)

    normal_vpin = book.calculate_vpin(BUCKET_SIZE, NUM_BUCKETS)
    print(f"  > Normal Flow VPIN Score: {normal_vpin:.4f} (Expected: Low, < 0.2)")

    print("\n  [Phase 2] Informed Trading / Toxic Flow (Heavy Sell-Off)")
    simulate_trades(book, 1001.0, num_trades=150, trade_size=100.0, buy_prob=0.10)

    toxic_vpin = book.calculate_vpin(BUCKET_SIZE, NUM_BUCKETS)
    print(f"  > Toxic Flow VPIN Score:   {toxic_vpin:.4f} (Expected: High, > 0.6)")

    print("\n  [HFT Strategy Action]")
    if toxic_vpin > 0.5:
        print("  🚨 HIGH TOXICITY DETECTED: Pulling all Market Maker quotes.")
        print("  🚨 ACTION: Widen spreads instantly to avoid adverse selection!")
    else:
        print("  ✅ MARKET STABLE: Continue providing tight spreads.")
        
    print("=======================================================\n")

if __name__ == "__main__":
    run_vpin_test()