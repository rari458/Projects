# main.py

import sys
import os

# Append the directory containing the compiled .so file
sys.path.append(os.path.abspath('./build/src'))

try:
    import FinancialEngine
except ImportError as e:
    print(f"[Error] Failed to import FinancialEngine C++ Core: {e}")
    sys.exit(1)

def main():
    print("==================================================")
    print("  Aladdin-Killer: Python <-> C++ Bridge Activated ")
    print("==================================================")

    # 1. Initialize the C++ Backtester from Python
    initial_capital = 100000.0
    strategy_name = "META_BRAIN"

    print(f"-> Booting C++ Engine with Strategy: {strategy_name}")
    engine = FinancialEngine.Backtester(initial_capital, strategy_name, 1.0)
    engine.set_regime_filter(False, 252)

    # 2. Feed Market Data
    print("-> Pushing Market Data to C++ Memory...")
    engine.on_market_data("SPY", 1.0, 450.0, 450.0, 450.0, 450.0)
    engine.on_market_data("TLT", 1.0, 100.0, 100.0, 100.0, 100.0)

    # 3. Fire Advanced 75-Strategy Events
    print("-> Firing Meta-Brain Event (Strategy #10: Risk Parity)...")
    meta_event = FinancialEngine.MetaEvent(
        FinancialEngine.MetaBrainType.RISK_PARITY,
        "",          # Target
        0.18,        # Equities Vol
        0.06,        # Bonds Vol
        2.0          # Timestamp
    )
    engine.send_meta_event(meta_event)

    # 4. Fetch Results back to Python
    equity = engine.get_total_equity()
    print(f"\n[Python State] Final Equity calculated by C++: ${equity:.2f}")

    spy_holdings = engine.get_holdings("SPY")
    tlt_holdings = engine.get_holdings("TLT")
    print(f"[Python State] SPY Holdings: {spy_holdings}")
    print(f"[Python State] TLT Holdings: {tlt_holdings}")

    # 5. Test C++ Analytics Engine purely from Python
    print("\n-> Testing C++ Analytics Engine...")
    prices = [100.0, 101.0, 102.5, 101.5, 103.0]
    returns = FinancialEngine.Analytics.calculate_log_returns(prices)
    vol = FinancialEngine.Analytics.calculate_volatility(returns)
    print(f"[Python State] Calculated Volatility via C++: {vol:.4f}")

if __name__ == "__main__":
    main()