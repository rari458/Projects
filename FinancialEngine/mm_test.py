import sys
import os

sys.path.append(os.path.abspath("build/src"))

try:
    import FinancialEngine as fe
except ImportError as e:
    print(f"[Error] Failed to load C++ Core: {e}")
    sys.exit(1)

def run_mm_test():
    print("\n=======================================================")
    print(" 🧠 MARKET MAKING: AVELLANEDA-STOIKOV INVENTORY MODEL")
    print("=======================================================")

    engine = fe.Backtester(100000.0, "MM", 1.0)
    engine.set_regime_filter(False)

    book = fe.OrderBook("SPY")

    def update_book_and_tick(timestamp, bid, ask):
        book.add_order(int(timestamp*1000), bid, 100.0, True, timestamp)
        book.add_order(int(timestamp*1000)+1, ask, 100.0, False, timestamp)
        engine.on_order_book_update(book, timestamp)

    print("\n  [Scenario 1] Neutral Inventory (Perfect Balance)")
    update_book_and_tick(1.0, 99.9, 100.1)

    print("\n  [Scenario 2] Accumulating Long Inventory (+100 shares)")
    engine.send_order("SPY", "BUY", 100.0, 100.0, 2.0)
    update_book_and_tick(2.0, 99.9, 100.1)

    print("\n  [Scenario 3] Toxic Flow! Massive Long Inventory (+500 shares)")
    engine.send_order("SPY", "BUY", 400.0, 100.0, 3.0)
    update_book_and_tick(3.0, 99.9, 100.1)

    print("\n  [Scenario 4] Trend Reversal! Short Inventory (-200 shares)")
    engine.send_order("SPY", "SELL", 700.0, 100.0, 4.0)
    update_book_and_tick(4.0, 99.9, 100.1)

    print("\n=======================================================\n")

if __name__ == "__main__":
    run_mm_test()