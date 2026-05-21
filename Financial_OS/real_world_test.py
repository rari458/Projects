import requests
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

BASE_URL = "http://localhost:8000/api"

def fetch_ohlc_history(symbol, start_date, end_date):
    print(f"  [Market Data] Downloading {symbol} ({start_date} ~ {end_date})...")
    ticker = yf.Ticker(symbol)
    hist = ticker.history(start=start_date, end=end_date)

    if hist.empty:
        return None

    return {
        "opens": hist['Open'].tolist(),
        "highs": hist['High'].tolist(),
        "lows": hist['Low'].tolist(),
        "closes": hist['Close'].tolist()
    }

def fetch_daily_returns(symbol, period="1y"):
    print(f"  [Market Data] Downloading {symbol} returns ({period})...")
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period=period)
    returns = hist['Close'].pct_change().dropna().tolist()
    return returns

def real_backtest(symbol="TSLA", start_date="2022-01-01", end_date="2022-12-31"):
    print(f"\n=======================================================")
    print(f" ⚔️  BEAR MARKET TEST: {symbol} ({start_date} ~ {end_date})  ⚔️")
    print(f"=======================================================")

    # 1. Get OHLC Data
    data_bundle = fetch_ohlc_history(symbol, start_date, end_date)
    if not data_bundle:
        print("Error: No data fetched.")
        return

    # 2. Benchmark (Buy & Hold uses Close)
    closes = data_bundle['closes']
    bh_return = ((closes[-1] - closes[0]) / closes[0]) * 100
    print(f"  [Benchmark] Buy & Hold Return: {bh_return:6.2f}%")
    print("-" * 55)

    initial_capital = 10000.0
    initial_shares = initial_capital / closes[0]
    benchmark_curve = [p * initial_shares for p in closes]

    plt.figure(figsize=(12, 6))
    plt.plot(benchmark_curve, label='Buy & Hold (Benchmark)', linestyle='--', color='gray', alpha=0.6)

    # 3. Strategy Comparison (Added 'VOL' for Volatility Breakout)
    strategies = [
        ("RSI", 1.0),
        ("MACD", 1.0),
        ("BB", 1.0),
        ("VOL", 1.0),
        ("OU", 1.0)
    ]
    results = {}

    for strat_name, lev in strategies:
        full_strat_name = f"{strat_name} (x{lev})"
        print(f"\n  >>> Testing Strategy: [ {full_strat_name} ]")

        payload = {
            "initial_capital": initial_capital,
            "opens": data_bundle['opens'],
            "highs": data_bundle['highs'],
            "lows": data_bundle['lows'],
            "closes": data_bundle['closes'],
            "strategy": strat_name,
            "leverage": lev
        }

        try:
            resp = requests.post(f"{BASE_URL}/backtest", json=payload)
            if resp.status_code == 200:
                data = resp.json()
                
                algo_return = data['return_pct']
                trades = data['total_trades']
                final_eq = data['final_equity']
                mdd = data.get('max_drawdown', 0.0)

                equity_curve = data.get('equity_curve', [])
                if equity_curve:
                    plt.plot(equity_curve, label=f'{full_strat_name} (Ret: {algo_return:.0f}%, MDD: {mdd:.1f}%)')
                
                results[full_strat_name] = algo_return

                print(f"    > Final Equity:    ${final_eq:,.2f}")
                print(f"    > Return:          {algo_return:6.2f}%")
                print(f"    > Max Drawdown:    {mdd:6.2f}%")
                print(f"    > Trades Executed: {trades}")
            else:
                print(f"    > API Error: {resp.text}")
                results[full_strat_name] = -999.0 # 에러 시 최하점
        except Exception as e:
            print(f"    > Connection Error: {e}")
            results[full_strat_name] = -999.0

    plt.title(f"Strategy Battle on {symbol}: Leverage Effect")
    plt.xlabel("Trading Days")
    plt.ylabel("Portfolio Value ($)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig("strategy_battle.png")
    print("\n  => 📊 Chart saved to 'strategy_battle.png'")

def run_portfolio_simulation(start_date="2022-01-01", end_date="2022-12-31"):
    print(f"\n=======================================================")
    print(f" 🛡️  PORTFOLIO DEFENSE TEST ({start_date} ~ {end_date}) 🛡️")
    print(f"=======================================================")

    portfolio = ["TSLA", "KO", "GLD", "SPY"]
    strategy = "MACD"
    leverage = 1.0
    capital_per_assist = 10000.0

    total_initial_capital = capital_per_assist * len(portfolio)
    portfolio_equity_curve = []

    plt.figure(figsize=(12, 6))
    final_results = {}

    print(f"  [Config] Strategy: {strategy}, Assets: {portfolio}")
    print(f"  [Config] Total Capital: ${total_initial_capital:,.2f}")
    print("-" * 60)

    for i, symbol in enumerate(portfolio):
        print(f"  >>> Processing Asset: {symbol}...")
        data_bundle = fetch_ohlc_history(symbol, start_date, end_date)

        if not data_bundle:
            print(f"    [Error] No data for {symbol}")
            continue

        payload = {
            "initial_capital": capital_per_assist,
            "opens": data_bundle['opens'],
            "highs": data_bundle['highs'],
            "lows": data_bundle['lows'],
            "closes": data_bundle['closes'],
            "strategy": strategy,
            "leverage": leverage
        }

        try:
            resp = requests.post(f"{BASE_URL}/backtest", json=payload)
            if resp.status_code == 200:
                data = resp.json()
                equity_curve = data.get('equity_curve', [])
                final_eq = data['final_equity']
                ret = data['return_pct']
                mdd = data.get('max_drawdown', 0.0)

                print(f"    > Return: {ret:6.2f}% | MDD: {mdd:6.2f}% | Final: ${final_eq:,.2f}")
                final_results[symbol] = final_eq

                if equity_curve:
                    plt.plot(equity_curve, label=f'{symbol} ({ret:.1f}%)', alpha=0.4, linestyle='--')
                    if len(portfolio_equity_curve) == 0:
                        portfolio_equity_curve = np.array(equity_curve)
                    else:
                        min_len = min(len(portfolio_equity_curve), len(equity_curve))
                        portfolio_equity_curve = portfolio_equity_curve[:min_len] + np.array(equity_curve[:min_len])

        except Exception as e:
            print(f"    [Connection Error] {e}")

    if len(portfolio_equity_curve) > 0:
        final_portfolio_value = portfolio_equity_curve[-1]
        portfolio_return = ((final_portfolio_value - total_initial_capital) / total_initial_capital) * 100
        print("=" * 60)
        print(f" 🏆 [PORTFOLIO RESULT] Total Return: {portfolio_return:6.2f}%")
        print("=" * 60)
        plt.plot(portfolio_equity_curve, label=f'TOTAL PORTFOLIO', linewidth=3, color='black')

    plt.savefig("portfolio_test.png")
    print(f"\n  => 📊 Chart saved to 'portfolio_test.png'")

def test_evolution(symbol="TSLA"):
    print(f"\n=======================================================")
    print(f" 🧬  AI EVOLUTION: {symbol}  🧬")
    print(f"=======================================================")

    data_bundle = fetch_ohlc_history(symbol, "2022-01-01", "2022-12-31")
    if not data_bundle: return

    payload = {
        "prices": data_bundle['closes'],
        "generations": 20,
        "population_size": 100
    }

    try:
        resp = requests.post(f"{BASE_URL}/evolve", json=payload)
        if resp.status_code == 200:
            res = resp.json()
            print(f"  > Best Params: {res['best_params']}")
            print(f"  > Best Return: {res['return_pct']:.2f}%")
        else:
            print(f"  > API Error: {resp.text}")
    except Exception as e:
        print(f"  > Connection Error: {e}")

def real_optimizer():
    symbols = ["AAPL", "MSFT", "NVDA", "GOOG", "AMZN", "TSLA", "BTC-USD"]
    print(f"\n=== [Real-World Optimizer] Finding Optimal Weights for {symbols} ===")

    assets_data = {}

    for sym in symbols:
        rets = fetch_daily_returns(sym, period="1y")
        if rets:
            assets_data[sym] = rets

    payload = {
        "assets": assets_data,
        "risk_free_rate": 0.045,
        "num_simulations": 100000
    }

    try:
        resp = requests.post(f"{BASE_URL}/optimize", json=payload)

        if resp.status_code == 200:
            data = resp.json()

            print(f"  > Max Sharpe Ratio: {data['max_sharpe']:.4f}")
            print(f"  > Exp. Annual Return: {data['expected_return']*100:.2f}%")
            print(f"  > Exp. Volatility:    {data['expected_volatility']*100:.2f}%")
            print("-" * 40)
            print("  [Optimal Allocation]")

            sorted_alloc = sorted(data['allocation'].items(), key=lambda x: x[1], reverse=True)
            for sym, weight in sorted_alloc:
                if weight > 0.001:
                    print(f"  > {sym:<8}: {weight*100:6.2f}%")

            labels = [x[0] for x in sorted_alloc if x[1] > 0.001]
            sizes = [x[1] for x in sorted_alloc if x[1] > 0.001]

            plt.figure(figsize=(10, 6))
            plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140)
            plt.title("AI Optimal Portfolio (Max Sharpe)")
            plt.savefig("real_portfolio.png")
            print("\n  => Chart saved to 'real_portfolio.png'")

        else:
            print(f"  > API Error: {resp.text}")

    except Exception as e:
        print(f"  > Connection Error: {e}")

if __name__ == "__main__":
    real_backtest("TSLA", "2022-01-01", "2022-12-31")
    real_optimizer()
    run_portfolio_simulation("2022-01-01", "2022-12-31")
    test_evolution("TSLA")