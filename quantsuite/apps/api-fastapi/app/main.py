# main.py

import json, os, subprocess, tempfile, shutil, random
from pathlib import Path
from typing import List, Tuple, Optional

from fastapi import FastAPI, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(title="QuantSuite API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _paths() -> Tuple[Path, Path, Path, Path]:
    app_dir  = Path(__file__).resolve().parent
    api_dir  = app_dir.parent
    apps_dir = api_dir.parent
    exe_path = apps_dir / "backtester-cpp" / "build" / "backtester"
    return app_dir, api_dir, apps_dir, exe_path

def _run_backtester(
    csv_paths: List[Path],
    out_path: Path,
    strategy: str,
    fast: int,
    slow: int,
    rsi_period: int,
    rsi_buy: float,
    rsi_sell: float,
    workdir: Path,
    weights: Optional[str] = None,
    risk_parity: bool = False,
):
    _, _, _, exe_path = _paths()

    args: List[str] = [str(exe_path), str(csv_paths[0]), str(out_path)]

    s = strategy.lower()
    if s == "ma":
        args += ["ma", str(fast), str(slow)]
    elif s == "rsi":
        args += ["rsi", str(rsi_period), str(rsi_buy), str(rsi_sell)]
    elif s == "macd":
        args += ["macd", str(fast), str(slow), str(rsi_period)]
    elif s == "boll":
        args += ["boll", str(fast), str(slow)]
    elif s == "donchian":
        args += ["donchian", str(fast)]
    elif s == "breakout":
        args += ["breakout", str(fast)]
    else:
        raise ValueError(f"unknown strategy: {strategy}")
    
    if len(csv_paths) > 1:
        args.append("--more")
        for p in csv_paths[1:]:
            args.append(str(p))

    if weights is not None:
        args += ["--weights", weights]

    if risk_parity:
        args.append("--risk-parity")

    print("[BACKTEST] args =", args)

    proc = subprocess.run(
        args,
        capture_output=True,
        text=True,
        cwd=str(workdir),
    )
    return proc

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/price")
def get_price(symbol: str = "AAPL"):
    price = round(random.uniform(100, 252), 2)
    return {"symbol": symbol, "price": price}

@app.get("/factor")
def get_factor(symbol: str = "AAPL", type: str = "momentum"):
    value = round(random.uniform(-0.05, 0.1), 4)
    return {"symbol": symbol, "factor": type, "value": value}

class PortfolioRequest(BaseModel):
    expected_returns: List[float]
    cov_flat: List[float]
    n: int

@app.post("/portfolio/optimize")
def optimize_portfolio(req: PortfolioRequest):
    n = req.n
    w = [1.0 / n] * n
    return {"weights": w}

@app.get("/backtest")
def run_backtest(
    symbol: str = Query("SP500"),
    strategy: str = Query("ma"),
    fast: int = Query(5, ge=1, le=252),
    slow: int = Query(20, ge=2, le=400),
    rsi_period: int = Query(14, ge=2, le=252),
    rsi_buy: float = Query(30.0, ge=0.0, le=50.0),
    rsi_sell: float = Query(70.0, ge=50.0, le=100.0),
):
    app_dir, api_dir, apps_dir, exe_path = _paths()

    csv_map = {
        "SP500": apps_dir / "sample_data" / "sp500_sample.csv",
    }
    csv_path = csv_map.get(symbol, csv_map["SP500"])
    out_path = api_dir / "result.json"

    print("[BACKTEST] exe =", exe_path)
    print("[BACKTEST] csv =", csv_path)
    print("[BACKTEST] out =", out_path)
    print("[BACKTEST] strategy =", strategy, "fast/slow=", fast, slow,
          "rsi_period =", rsi_period, "rsi_buy/sell =", rsi_buy, rsi_sell)
    
    if not exe_path.exists():
        return JSONResponse({"error": "backtester not found", "path": str(exe_path)}, status_code=500)
    if not csv_path.exists():
        return JSONResponse({"error": "csv not found", "path": str(csv_path)}, status_code=500)
    if strategy.lower() == "ma" and fast >= slow:
        return JSONResponse({"error": "for MA strategy, fast must be < slow"}, status_code=400)
    
    try:
        proc = _run_backtester(
            [csv_path],
            out_path,
            strategy=strategy,
            fast=fast,
            slow=slow,
            rsi_period=rsi_period,
            rsi_buy=rsi_buy,
            rsi_sell=rsi_sell,
            workdir=api_dir,
        )
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    
    if proc.returncode != 0:
        return JSONResponse(
            {
                "error": "subprocess failed",
                "code": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr
            },
            status_code=500,
        )
    
    try:
        with open(out_path, "r") as f:
            result = json.load(f)
        result.update({"symbol": symbol})
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse({"error": f"read-json failed: {e}", "out_path": str(out_path)}, status_code=500)
    
@app.post("/backtest/upload")
async def backtest_upload(
    file: UploadFile = File(...),
    strategy: str = Query("ma"),
    fast: int = Query(5, ge=1, le=252),
    slow: int = Query(20, ge=2, le=400),
    rsi_period: int = Query(14, ge=2, le=252),
    rsi_buy: float = Query(30.0, ge=0.0, le=50.0),
    rsi_sell: float = Query(70.0, ge=50.0, le=100.0),
):
    app_dir, api_dir, apps_dir, exe_path = _paths()
    out_path = api_dir / "result.json"

    if not exe_path.exists():
        return JSONResponse({"error": "backtester not found", "path": str(exe_path)}, status_code=500)
    if strategy.lower() == "ma" and fast >= slow:
        return JSONResponse({"error": "for MA strategy, fast must be < slow"}, status_code=400)
    if file.filename and not file.filename.lower().endswith(".csv"):
        return JSONResponse({"error": "only .csv are accepted"}, status_code=400)
    
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            tmp_path = Path(tmp.name)
            try:
                file.file.seek(0)
            except Exception:
                pass
            shutil.copyfileobj(file.file, tmp)

        print("[UPLOAD] csv =", tmp_path)
        print("[UPLOAD] out =", out_path)

        try:
            proc = _run_backtester(
                [tmp_path],
                out_path,
                strategy=strategy,
                fast=fast,
                slow=slow,
                rsi_period=rsi_period,
                rsi_buy=rsi_buy,
                rsi_sell=rsi_sell,
                workdir=api_dir,
            )
        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=400)
        
        if proc.returncode != 0:
            return JSONResponse(
                {
                    "error": "subprocess failed",
                    "code": proc.returncode,
                    "stdout": proc.stdout,
                    "stderr": proc.stderr
                },
                status_code=500,
            )
        
        with open(out_path, "r") as f:
            result = json.load(f)
        result.update({"symbol": f"UPLOAD:{file.filename or 'uploaded.csv'}"})
        return JSONResponse(content=result)
    
    except Exception as e:
        return JSONResponse({"error": f"upload-failed: {e}"}, status_code=500)
    
    finally:
        try:
            await file.close()
        except Exception:
            pass
        if tmp_path:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass

class PortfolioBacktestRequest(BaseModel):
    symbols: List[str]
    strategy: str = "ma"
    fast: int = 5
    slow: int = 20
    rsi_period: int = 14
    rsi_buy: float = 30.0
    rsi_sell: float = 70.0
    weights: Optional[List[float]] = None
    weight_mode: Optional[str] = None

@app.post("/backtest/portfolio")
async def backtest_portfolio(req: PortfolioBacktestRequest):
    app_dir, api_dir, apps_dir, exe_path = _paths()

    csv_map = {
        "SP500": apps_dir / "sample_data" / "sp500_sample.csv",
    }

    if not exe_path.exists():
        return JSONResponse({"error": "backtester not found", "path": str(exe_path)}, status_code=500)
    
    if req.strategy.lower() == "ma" and req.fast >= req.slow:
        return JSONResponse({"error": "for MA strategy, fast must be < slow"}, status_code=400)
    
    csv_paths: List[Path] = []
    for sym in req.symbols:
        p = csv_map.get(sym, csv_map["SP500"])
        if not p.exists():
            return JSONResponse({"error": "csv not found", "symbol": sym, "path": str(p)}, status_code=500)
        csv_paths.append(p)

    out_path = api_dir / "result.json"

    use_risk_parity = (req.weight_mode == "risk_parity")

    weights_arg = None
    if not use_risk_parity and req.weights is not None:
        if len(req.weights) != len(req.symbols):
            return JSONResponse(
                {"error": f"weights length must match symbols length ({len(req.symbols)})"},
                status_code=400
            )
        
        total = sum(req.weights)
        if total <= 0:
            return JSONResponse(
                {"error": "weights sum must be positive"}, 
                status_code=400
            )
        
        norm = [w / total for w in req.weights]
        weights_arg = ",".join(f"{w:.6f}" for w in norm)

    try:
        proc = _run_backtester(
            csv_paths,
            out_path,
            strategy=req.strategy,
            fast=req.fast,
            slow=req.slow,
            rsi_period=req.rsi_period,
            rsi_buy=req.rsi_buy,
            rsi_sell=req.rsi_sell,
            workdir=api_dir,
            weights=weights_arg,
            risk_parity=use_risk_parity,
        )

    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)

    if proc.returncode != 0:
        return JSONResponse(
            {
                "error": "subprocess failed",
                "code": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
            },
            status_code=500,
        )

    try:
        with open(out_path, "r") as f:
            result = json.load(f)

        result.update({"symbols": req.symbols})
        return JSONResponse(content=result)
    
    except Exception as e:
        return JSONResponse({"error": f"read-json failed: {e}", "out_path": str(out_path)}, status_code=500)