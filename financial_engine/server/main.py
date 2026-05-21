import sys
import os
from typing import List, Dict
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Ensure Python can find the C++ module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../build/src")))

try:
    import FinancialEngine as fe
    print("[System] Financial Engine Core Loaded Successfully (Multi-Asset Ready).")
except ImportError as e:
    print(f"[Critical Error] Failed to load C++ Core: {e}")
    sys.exit(1)

app = FastAPI(title="Financial OS API", version="2.0.0")

# --- Data Models ---
class AssetData(BaseModel):
    opens: List[float]
    highs: List[float]
    lows: List[float]
    closes: List[float]

class BacktestRequest(BaseModel):
    initial_capital: float = 10000.0
    assets: Dict[str, AssetData]
    strategy: str = "EMA"
    leverage: float = 1.0
    max_drawdown_limit: float = 0.10
    pairs_window: int = 30
    pairs_threshold: float = 2.0

class OptimizationRequest(BaseModel):
    assets: Dict[str, List[float]] 
    risk_free_rate: float = 0.02
    num_simulations: int = 10000

class EvolutionRequest(BaseModel):
    prices: List[float]
    generations: int = 20
    population_size: int = 100

class ScanRequest(BaseModel):
    assets: Dict[str, AssetData]

class RegimeRequest(BaseModel):
    prices: List[float]
    window_size: int = 20

# --- API Endpoints ---

@app.get("/")
def read_root():
    return {"status": "online", "engine": "C++ High-Performance Core (Multi-Asset)"}

@app.post("/api/backtest")
def run_backtest(req: BacktestRequest):
    try:
        # 1. Initialize C++ Engine
        engine = fe.Backtester(req.initial_capital, req.strategy, req.leverage)
        engine.set_risk_params(req.max_drawdown_limit, 0.02)

        if req.strategy == "PAIRS":
            engine.set_pairs_parameters(req.pairs_window, req.pairs_threshold)
        
        # 2. Feed Data
        if not req.assets:
            raise HTTPException(status_code = 400, detail="No assets provided")

        first_symbol = list(req.assets.keys())[0]
        data_len = len(req.assets[first_symbol].closes)

        for t in range(data_len):
            timestamp = float(t)
            for symbol, data in req.assets.items():
                if t < len(data.closes):
                    engine.on_market_data(
                        symbol,
                        timestamp,
                        data.opens[t],
                        data.highs[t],
                        data.lows[t],
                        data.closes[t]
                    )
            
        # 3. Retrieve Raw Data from C++
        final_equity = engine.get_total_equity()
        raw_trades = engine.get_trade_history()
        mdd = engine.get_max_drawdown()
        equity_history = engine.get_equity_history()

        # 4. [CRITICAL STEP] Convert C++ Objects to Python Dictionaries
        # We MUST convert them manually, or FastAPI will crash.
        clean_trade_list = []
        for tr in raw_trades:
            clean_trade_list.append({
                "id": tr.id,
                "symbol": tr.symbol,
                "side": tr.side,
                "qty": float(tr.quantity),
                "price": float(tr.price),
                "comm": float(tr.commission),
                "time": float(tr.timestamp)
            })

        # 5. Return the CLEAN Python dictionary
        return {
            "status": "success",
            "strategy": req.strategy,
            "final_equity": final_equity,
            "return_pct": ((final_equity - req.initial_capital) / req.initial_capital) * 100,
            "max_drawdown": mdd * 100.0,
            "total_trades": len(clean_trade_list),
            "equity_history": equity_history,
            "trade_history": clean_trade_list
        }

    except Exception as e:
        print(f"[Server Error] {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/optimize")
def run_optimizer(req: OptimizationRequest):
    try:
        if not req.assets:
            raise HTTPException(status_code=400, detail="No asset data provided")

        opt = fe.Optimizer()
        assets_list = []
        for symbol, returns in req.assets.items():
            opt.add_asset(symbol, returns)
            assets_list.append(symbol)
            
        result = opt.optimize_sharpe_ratio(req.num_simulations, req.risk_free_rate)
        
        allocation = {}
        for i, symbol in enumerate(assets_list):
            allocation[symbol] = result.optimal_weights[i]

        return {
            "status": "success",
            "num_simulations": req.num_simulations,
            "max_sharpe": result.sharpe_ratio,
            "expected_return": result.portfolio_return,
            "expected_volatility": result.portfolio_volatility,
            "allocation": allocation
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/evolve")
def run_evolution(req: EvolutionRequest):
    best = fe.GeneticOptimizer.evolve_macd(req.prices, 10000.0, req.generations, req.population_size)
    return {
        "best_params": {"fast": best.fast, "slow": best.slow, "signal": best.signal},
        "return_pct": best.fitness
    }

@app.post("/api/scan")
def scan_universe(req: ScanRequest):
    try:
        price_map = {}
        for symbol, data in req.assets.items():
            if not data.closes: continue
            price_map[symbol] = data.closes

        if len(price_map) < 2:
            raise HTTPException(status_code=400, detail="Need at least 2 assets to scan.")

        top_pairs = fe.PairSelector.find_top_pairs(price_map, 5)

        results = []
        for p in top_pairs:
            results.append({
                "asset_a": p.asset_a,
                "asset_b": p.asset_b,
                "correlation": p.correlation,
                "beta": p.beta,
                "r_squared": p.r_squared
            })

        return {
            "status": "success",
            "scanned_count": len(price_map),
            "top_pairs": results
        }

    except Exception as e:
        print(f"[Scan Error] {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/regime")
def detect_market_regime(req: RegimeRequest):
    try:
        if not req.prices:
            raise HTTPException(status_code=400, detail="No price data provided")

        result = fe.RegimeDetector.detect_regime(req.prices, req.window_size)

        return {
            "status": "success",
            "state_id": result.state_id,
            "state_name": result.state_name,
            "current_volatility": result.current_volatility,
            "current_trend": result.current_trend
        }
    except Exception as e:
        print(f"[Regime Error] {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)