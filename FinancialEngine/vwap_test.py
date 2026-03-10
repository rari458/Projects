import sys
import os
import math
import random

sys.path.append(os.path.abspath("build/src"))

try:
    import FinancialEngine as fe
except ImportError as e:
    print(f"[Error] Failed to load C++ Core: {e}")
    sys.exit(1)

def run_vwap_test():
    print("\n=======================================================")
    print(" 🎯 HFT EXECUTION: VWAP SNIPER ALGORITHM")
    print("=======================================================")

    engine = fe.Backtester(2000000.0, "VWAP", 1.0)
    engine.set_regime_filter(False)

    book = fe.OrderBook("SPY")
    base_price = 100.0

    print("  [System] Simulating Intraday Market Flow & VWAP Tracking...\n")

    for i in range(1, 201):
        timestamp = float(i)

        noise = random.uniform(-0.5, 0.5)
        current_price = base_price + 3.0 * math.sin(i / 15.0) + noise

        bid_price = current_price - 0.05
        ask_price = current_price + 0.05
        book.add_order(i * 10, bid_price, 2000.0, True, timestamp)
        book.add_order(i * 10 + 1, ask_price, 2000.0, False, timestamp)

        market_vol = random.uniform(100.0, 2000.0)
        book.execute_trade(current_price, market_vol, timestamp)
        
        engine.on_order_book_update(book, timestamp)

        book.cancel_order(i * 10, timestamp)
        book.cancel_order(i * 10 + 1, timestamp)

    market_vwap = book.calculate_vwap()

    trades = engine.get_trade_history()
    total_shares = sum(t.quantity for t in trades)
    total_spent = sum(t.quantity * t.price for t in trades)

    engine_avg_price = (total_spent / total_shares) if total_shares > 0 else 0.0
    slippage_savings = (market_vwap - engine_avg_price) * total_shares

    print("\n=======================================================")
    print(" 📊 VWAP EXECUTION PERFORMANCE REPORT")
    print("=======================================================")
    print(f"  > Market Daily VWAP:    ${market_vwap:.4f}")
    print(f"  > Engine Average Price: ${engine_avg_price:.4f}")
    print(f"  > Total Shares Bought:  {total_shares:,.0f} / 10,000")
    print("-" * 55)
    
    if engine_avg_price < market_vwap:
        print(f"  ✅ SUCCESS: Beat the market VWAP by ${(market_vwap - engine_avg_price):.4f} per share.")
        print(f"  💰 Implicit Savings: +${slippage_savings:,.2f} (Reduced Market Impact)")
    else:
        print("  ❌ FAILED: Executed worse than market VWAP.")
        
    print("=======================================================\n")

if __name__ == "__main__":
    run_vwap_test()