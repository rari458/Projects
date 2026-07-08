# services/gateway.py

from fastapi import FastAPI
from pydantic import BaseModel
from celery import Celery
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