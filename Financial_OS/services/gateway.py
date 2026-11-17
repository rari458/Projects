# services/gateway.py

from fastapi import FastAPI
from pydantic import BaseModel, Field
from datetime import date
from typing import Literal
from celery import Celery, chord
from celery.result import AsyncResult
from prometheus_fastapi_instrumentator import Instrumentator
import os

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
celery_client = Celery("financial_os", broker=REDIS_URL, backend=REDIS_URL)

app = FastAPI(title="Financial OS Gateway", version="3.0.0")
Instrumentator().instrument(app).expose(app)
@app.get("/health")
def health():
    return {"status": "ok"}

class JobRequest(BaseModel):
    symbols: list[str] = Field(min_length=1)
    start: str | None = None
    end: str | None = None
    strategy: str = "MACD"
    initial_capital: float = 100000.0
    leverage: float = 1.0

@app.post("/jobs")
def submit_job(req: JobRequest):
    async_result = celery_client.send_task(
        "run_backtest_job",
        args=[req.symbols, req.start, req.end,
              req.strategy, req.initial_capital, req.leverage],
    )
    return {"job_id": async_result.id, "state": "PENDING"}

@app.get("/jobs/{job_id}")
def job_status(job_id: str):
    res = AsyncResult(job_id, app=celery_client)
    payload = {"job_id": job_id, "state": res.state}
    if res.successful():
        payload["result"] = res.result
    elif res.failed():
        payload["error"] = str(res.result)
    return payload

def _add_months(d: date, months: int) -> date:
    total = d.month - 1 + months
    year  = d.year + total // 12
    return date(year, total % 12 + 1, min(d.day, 28))

def _walkforward_windows(start, end, test_months, step_months):
    s = date.fromisoformat(start)
    e = date.fromisoformat(end)
    windows = []
    ws = s
    while _add_months(ws, test_months) <= e:
        windows.append((ws.isoformat(), _add_months(ws, test_months).isoformat()))
        ws = _add_months(ws, step_months)
    return windows

class WalkforwardRequest(BaseModel):
    symbols: list[str] = Field(min_length=1)
    start: str
    end: str
    strategy: str = "MACD"
    test_months: int = 3
    step_months: int = 3
    initial_capital: float = 100000.0
    leverage: float = 1.0

@app.post("/walkforward")
def submit_walkforward(req: WalkforwardRequest):
    windows = _walkforward_windows(req.start, req.end, req.test_months, req.step_months)
    
    if not windows:
        return {"state": "ERROR", "error": "date range too short for one test window"}
    header = [
        celery_client.signature(
            "run_backtest_job",
            args=[
                req.symbols, ws, we, req.strategy,
                req.initial_capital, req.leverage
            ],
        )
        for (ws, we) in windows
    ]
    callback = celery_client.signature("aggregate_walkforward")
    async_result = chord(header, app=celery_client)(callback)
    return {"job_id": async_result.id, "state": "PENDING", "num_windows": len(windows)}

def _wf_train_test_windows(start, end, train_months, test_months, step_months):
    s = date.fromisoformat(start)
    e = date.fromisoformat(end)
    windows = []
    train_start = s
    while True:
        test_start = _add_months(train_start, train_months)
        test_end = _add_months(test_start, test_months)
        if test_end > e:
            break
        windows.append((train_start.isoformat(), test_start.isoformat(),
                        test_start.isoformat(), test_end.isoformat()))
        train_start = _add_months(train_start, step_months)
    return windows

DEFAULT_CANDIDATES = ["EMA", "RSI", "MACD", "BB", "VOL", "OU"]

class WfSelectRequest(BaseModel):
    symbols: list[str] = Field(min_length=1)
    start: str
    end: str
    candidates: list[str] = Field(default=DEFAULT_CANDIDATES, min_length=1)
    train_months: int = 12
    test_months: int = 6
    step_months: int = 6
    initial_capital: float = 100000.0
    leverage: float = 1.0

@app.post("/wf_select")
def submit_wf_select(req: WfSelectRequest):
    windows = _wf_train_test_windows(req.start, req.end, req.train_months,
                                     req.test_months, req.step_months)

    if not windows:
        return {"state": "ERROR", "error": "date range too short for one train+test window"}                                    
    header = [
        celery_client.signature(
            "run_wf_window",
            args=[
                req.symbols, tr_s, tr_e, te_s, te_e,
                req.candidates, req.initial_capital, req.leverage
            ],
        )
        for (tr_s, tr_e, te_s, te_e) in windows
    ]
    callback = celery_client.signature("aggregate_wf_selection")
    async_result = chord(header, app=celery_client)(callback)
    return {"job_id": async_result.id, "state": "PENDING", "num_windows": len(windows)}

OptimizeMethod = Literal[
    "mc_sharpe", "inverse_vol", "min_variance",
    "max_sharpe_analytic", "max_sharpe_shrunk", "max_sharpe_robust",
]
    
class OptimizeRequest(BaseModel):
    symbols: list[str] = Field(min_length=1)
    start: str | None = None
    end: str | None = None
    method: OptimizeMethod = "mc_sharpe"
    # Bounds worker memory: the MC search keeps num_simulations x len(symbols) weights.
    num_simulations: int = Field(default=100000, ge=1, le=1_000_000)
    risk_free_rate: float = 0.02
    # The engine treats num_threads as a switch: 1 = one thread, anything else =
    # a pool of hardware_concurrency() threads. Only these two values mean anything.
    # Left out, the worker uses its deployment's FOS_OPTIMIZE_THREADS (Compose 0,
    # k8s, 1), because only the deployment knows how much CPU a worker has.
    num_threads: Literal[0, 1] | None = None
    
@app.post("/optimize")
def submit_optimize(req: OptimizeRequest):
    async_result = celery_client.send_task(
        "run_optimize_job",
        args=[req.symbols, req.start, req.end, req.method, 
            req.num_simulations, req.risk_free_rate, req.num_threads],
        )
    return {"job_id": async_result.id, "state": "PENDING"}

IngestPeriod = Literal["1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max"]

class IngestRequest(BaseModel):
    symbols: list[str] = Field(min_length=1, max_length=100)
    period: IngestPeriod = "5y"

@app.post("/ingest")
def submit_ingest(req: IngestRequest):
    # Explicit queue: only the ingester consumes "ingest", so the one writer the
    # snapshot design relies on is the only process that ever runs this task.
    async_result = celery_client.send_task(
        "ingest_symbols", args=[req.symbols, req.period], queue="ingest",
    )
    return {"job_id": async_result.id, "state": "PENDING"}
