import sys
import os
import numpy as np
import matplotlib.pyplot as plt

# C++ 모듈 경로 설정
sys.path.append(os.path.abspath("build/src"))
import FinancialEngine as fe

def run_backtest():
    print("=== Financial Engine: Event-Driven Backtester Test ===\n")

    initial_capital = 10000.0
    engine = fe.Backtester(initial_capital)
    print(f"Initial Capital: ${initial_capital:,.2f}")

    # ---------------------------------------------------------
    # [Fix] 현실적인 주가 데이터 생성 (Random Walk with Drift)
    # ---------------------------------------------------------
    np.random.seed(42) # 결과 재현을 위해 시드 고정
    days = 500         # 추세가 형성되도록 기간을 늘림
    
    # 상승장(Bull Market) 가정
    mu = 0.15    # 연 기대 수익률 15%
    sigma = 0.20 # 연 변동성 20%
    dt = 1/252   # 1일
    
    prices = []
    current_price = 100.0
    
    print(f"Generating {days} days of realistic market data...")
    
    for _ in range(days):
        prices.append(current_price)
        # 기하 브라운 운동 (GBM) 수식 적용
        drift = (mu - 0.5 * sigma**2) * dt
        shock = sigma * np.sqrt(dt) * np.random.normal()
        current_price *= np.exp(drift + shock)

    # ---------------------------------------------------------

    portfolio_values = []
    
    for i, price in enumerate(prices):
        engine.on_market_data(float(i), price)
        portfolio_values.append(engine.get_total_equity())

    # 결과 분석
    trades = engine.get_trade_history()
    final_equity = engine.get_total_equity()
    return_pct = ((final_equity - initial_capital) / initial_capital) * 100
    
    # 벤치마크 (Buy & Hold) 수익률 비교
    bh_return = ((prices[-1] - prices[0]) / prices[0]) * 100

    print("\n[Backtest Results]")
    print(f"Final Equity:    ${final_equity:,.2f}")
    print(f"Total Return:    {return_pct:.2f}%")
    print(f"Buy & Hold Ret:  {bh_return:.2f}%")
    print(f"Total Trades:    {len(trades)}")
    
    if len(trades) > 0:
        print("\n[Trade History]")
        print(f"{'Time':<5} | {'Side':<4} | {'Price':<10} | {'Qty':<10} | {'Comm'}")
        print("-" * 55)
        for trade in trades:
            print(f"{int(trade.timestamp):<5} | {trade.side:<4} | ${trade.price:<9.2f} | {trade.quantity:<10.4f} | ${trade.commission:.2f}")

    # 시각화
    plt.figure(figsize=(12, 8))
    
    plt.subplot(2, 1, 1)
    plt.plot(prices, label='Market Price', color='black', alpha=0.6)
    
    # 시각화용 EMA 계산 (단순 참조용, 실제 계산은 C++ 엔진이 수행함)
    s_window, l_window = 20, 50
    ema_short = [prices[0]]
    ema_long = [prices[0]]
    alpha_s = 2/(s_window+1)
    alpha_l = 2/(l_window+1)
    
    for p in prices[1:]:
        ema_short.append((p - ema_short[-1])*alpha_s + ema_short[-1])
        ema_long.append((p - ema_long[-1])*alpha_l + ema_long[-1])
        
    plt.plot(ema_short, label='EMA 20', color='orange', alpha=0.8, linewidth=1)
    plt.plot(ema_long, label='EMA 50', color='green', alpha=0.8, linewidth=1)

    if len(trades) > 0:
        buy_x = [t.timestamp for t in trades if t.side == "BUY"]
        buy_y = [t.price for t in trades if t.side == "BUY"]
        sell_x = [t.timestamp for t in trades if t.side == "SELL"]
        sell_y = [t.price for t in trades if t.side == "SELL"]
        
        plt.scatter(buy_x, buy_y, marker='^', color='green', s=100, label='BUY', zorder=5)
        plt.scatter(sell_x, sell_y, marker='v', color='red', s=100, label='SELL', zorder=5)
    
    plt.title("Trend Following Strategy (Geometric Brownian Motion Data)")
    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.subplot(2, 1, 2)
    plt.plot(portfolio_values, label='Strategy Equity', color='blue')
    plt.plot([initial_capital * (p/prices[0]) for p in prices], label='Buy & Hold Equity', color='gray', linestyle='--')
    plt.title("Performance Comparison")
    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("backtest_result_realistic.png")
    print(f"\n[Visualization] Chart saved to 'backtest_result_realistic.png'")

if __name__ == "__main__":
    run_backtest()