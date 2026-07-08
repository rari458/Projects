# services/gateway.py

from fastapi import FastAPI
from pydantic import BaseModel
from datetime import date
from celery import Celery, chord
from celery.result import AsyncResult
import os

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
celery_client = Celery("financial_os", broker=REDIS_URL, backend=REDIS_URL)

app = FastAPI(title="Financial OS Gateway", version="3.0.0")

class JobRequest(BaseModel):
    symbols: list[str]
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
    symbols: list[str]
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
    symbols: list[str]
    start: str
    end: str
    candidates: list[str] = DEFAULT_CANDIDATES
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