# services/tasks.py

import FinancialEngine as fe
import data_store
from services.celery_app import celery_app

def _run_backtest(con, symbols, start, end, strategy, initial_capital, leverage):
    engine = fe.Backtester(initial_capital, strategy, leverage)
    series = {sym: data_store.get_ohlc(con, sym, start=start, end=end)
              for sym in symbols}
    n = min(len(s["closes"]) for s in series.values())
    for i in range(n):
        for sym in symbols:
            bars = series[sym]
            engine.on_market_data(
                sym, float(i),
                bars["opens"][i], bars["highs"][i],
                bars["lows"][i], bars["closes"][i],
            )
    trades = []
    for tr in engine.get_trade_history():
        trades.append({
            "id": tr.id, "symbol": tr.symbol, "side": tr.side,
            "qty": float(tr.quantity), "price": float(tr.price),
            "comm": float(tr.commission), "time": float(tr.timestamp),
        })
    final_equity = engine.get_total_equity()
    return {
        "symbols": symbols,
        "strategy": strategy,
        "window_start": start,
        "window_end": end,
        "bars": n,
        "final_equity": final_equity,
        "return_pct": (final_equity - initial_capital) / initial_capital * 100.0,
        "max_drawdown": engine.get_max_drawdown() * 100.0,
        "total_trades": len(trades),
        "trades": trades,
    }

@celery_app.task(name="run_backtest_job")
def run_backtest_job(symbols, start, end, strategy="MACD",
                     initial_capital=100000.0, leverage=1.0):
    con = data_store.connect_readonly()
    try:
        return _run_backtest(con, symbols, start, end, strategy, initial_capital, leverage)
    finally:
        con.close()                     

@celery_app.task(name="aggregate_walkforward")
def aggregate_walkforward(window_results):
    growth = 1.0
    per_window = []
    for r in window_results:
        growth *= 1.0 + r["return_pct"] / 100.0
        per_window.append({
            "start": r["window_start"],
            "end": r["window_end"],
            "return_pct": r["return_pct"],
            "trades": r["total_trades"],
        })
    best  = max(per_window, key=lambda w: w["return_pct"])
    worst = min(per_window, key=lambda w: w["return_pct"])
    return {
        "num_windows": len(per_window),
        "compounded_oos_return_pct": (growth - 1.0) * 100.0,
        "best_window": best,
        "worst_window": worst,
        "windows": per_window,
    }

@celery_app.task(name="run_wf_window")
def run_wf_window(symbols, train_start, train_end, test_start, test_end,
                  candidates, initial_capital=100000.0, leverage=1.0):
    con = data_store.connect_readonly()
    try:
        in_sample = {}
        for strat in candidates:
            r = _run_backtest(con, symbols, train_start, train_end, strat, 
                              initial_capital, leverage)
            in_sample[strat] = r["return_pct"]
        chosen = max(in_sample, key=in_sample.get)
        oos = _run_backtest(con, symbols, test_start, test_end, chosen,
                            initial_capital, leverage)
        return {
            "test_start": test_start,
            "test_end": test_end,
            "chosen": chosen,
            "is_return_pct": in_sample[chosen],
            "oos_return_pct": oos["return_pct"],
            "oos_trades": oos["total_trades"],
            "in_sample": in_sample,
        }                          
    finally:
        con.close()

@celery_app.task(name="aggregate_wf_selection")  
def aggregate_wf_selection(window_results):
    growth = 1.0
    per_window = []
    for r in window_results:
        growth *= 1.0 + r["oos_return_pct"] / 100.0
        per_window.append({
            "test_start": r["test_start"],
            "test_end": r["test_end"],
            "chosen": r["chosen"],
            "is_return_pct": r["is_return_pct"],
            "oos_return_pct": r["oos_return_pct"],
            "oos_trades": r["oos_trades"],
        })
    picks = {}
    for w in per_window:
        picks[w["chosen"]] = picks.get(w["chosen"], 0) + 1
    return {
        "num_windows": len(per_window),
        "adaptive_compounded_oos_pct": (growth - 1.0) * 100.0,
        "strategy_picks": picks,
        "windows": per_window,
    }