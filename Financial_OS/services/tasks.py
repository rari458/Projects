# services/tasks.py

import FinancialEngine as fe
import data_store
from services.celery_app import celery_app

@celery_app.task(name="run_backtest_job")
def run_backtest_job(symbols, start, end, strategy="MACD",
                     initial_capital=100000.0, leverage=1.0):
    con = data_store.connect_readonly()
    try:
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
            "bars": n,
            "final_equity": final_equity,
            "return_pct": (final_equity - initial_capital) / initial_capital * 100.0,
            "max_drawdown": engine.get_max_drawdown() * 100.0,
            "total_trades": len(trades),
            "trades": trades,
        }
    finally:
        con.close()