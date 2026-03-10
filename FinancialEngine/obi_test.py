import sys
import os

sys.path.append(os.path.abspath("build/src"))

try:
    import FinancialEngine as fe
except ImportError as e:
    print(f"[Error] Failed to load C++ Core: {e}")
    sys.exit(1)

def run_obi_test():
    print("\n=======================================================")
    print(" ⚡ L2 MICROSTRUCTURE: ORDER BOOK IMBALANCE (OBI)")
    print("=======================================================")

    book = fe.OrderBook("SPY")
    order_id = 1

    print("  [Phase 1] Building Balance Market (Normal State)")
    
    book.add_order(order_id:=1, 99.9, 100.0, True, 1000.0)
    book.add_order(order_id:=2, 99.8, 150.0, True, 1000.1)
    book.add_order(order_id:=3, 99.7, 200.0, True, 1000.2)

    book.add_order(order_id:=4, 100.1, 100.0, False, 1000.3)
    book.add_order(order_id:=5, 100.2, 160.0, False, 1000.4)
    book.add_order(order_id:=6, 100.3, 190.0, False, 1000.5)

    mid_price = book.get_mid_price()
    obi = book.calculate_imbalance(levels=3)
    print(f"  > Mid Price: ${mid_price:.2f}")
    print(f"  > OBI Score:  {obi:+.4f} (Expectes: ~0.0, Neutral)")

    print("\n  [Phase 2] Institutional Buy Wall Appears (Heavy Buy Pressure)")
    institutional_bid_id = 7
    book.add_order(institutional_bid_id, 99.9, 5000.0, True, 1000.6)

    obi = book.calculate_imbalance(levels=3)
    action = "LONG (Front-run the massive bid)" if obi > 0.5 else "WAIT"
    print(f"  > OBI Score:  {obi:+.4f} -> Market heavily skewed to BUY")
    print(f"  > HFT Action: {action}")

    print("\n  [Phase 3] Spoofing Detected! (Flash Crash Scenario)")
    book.cancel_order(institutional_bid_id, 1000.7)
    book.add_order(order_id:=8, 100.1, 3000.0, False, 1000.8)
    book.add_order(order_id:=9, 100.2, 4000.0, False, 1000.9)

    obi = book.calculate_imbalance(levels=3)
    action = "SHORT (Liquidation cascade expected)" if obi < -0.5 else "WAIT"
    print(f"  > OBI Score:  {obi:+.4f} -> Market heavily skewed to SELL")
    print(f"  > HFT Action: {action}")
    print("=======================================================\n")

if __name__ == "__main__":
    run_obi_test()