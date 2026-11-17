# services/tests/test_gateway.py

from datetime import date
import ast
import typing
from pathlib import Path
import pytest
from pydantic import ValidationError
from services import gateway
from services.gateway import _add_months, _walkforward_windows, _wf_train_test_windows

def test_add_months_basic():
    assert _add_months(date(2020, 1, 15), 1) == date(2020, 2, 15)

def test_add_months_year_rollover():
    assert _add_months(date(2020, 12, 1), 1) == date(2021, 1, 1)

def test_add_months_multi_year():
    assert _add_months(date(2020, 1, 1), 25) == date(2022, 2, 1)

def test_add_months_zero():
    assert _add_months(date(2020, 5, 10), 0) == date(2020, 5, 10)

def test_add_months_clamps_day_to_28():
    assert _add_months(date(2020, 1, 30), 1) == date(2020, 2, 28)
    assert _add_months(date(2020, 1, 31), 1) == date(2020, 2, 28)

def test_walkforward_windows_matches_verified_run():
    windows = _walkforward_windows("2020-01-01", "2024-12-31", 3, 3)
    assert len(windows) == 19
    assert windows[0]  == ("2020-01-01", "2020-04-01")
    assert windows[-1] == ("2024-07-01", "2024-10-01")

def test_walkforward_windows_empty_when_range_too_short():
    assert _walkforward_windows("2024-01-01", "2024-02-01", 3, 3) == []

def test_wf_train_test_windows_matches_verified_default_run():
    windows = _wf_train_test_windows("2020-01-01", "2024-12-31", 12, 6, 6)
    assert len(windows) == 7
    assert windows[0] == ("2020-01-01", "2021-01-01", "2021-01-01", "2021-07-01")

def test_wf_train_test_windows_matches_verified_stress_run():
    windows = _wf_train_test_windows("2020-01-01", "2024-12-31", 12, 6, 1)
    assert len(windows) == 42

def test_wf_train_test_windows_empty_when_range_too_short():
    assert _wf_train_test_windows("2024-01-01", "2024-06-01", 12, 6, 6) == []
    
def _optimize_request(**overrides):
    return gateway.OptimizeRequest(**{"symbols": ["SPY", "AAPL", "MSFT"], **overrides})

def test_optimize_request_defaults():
    req = _optimize_request()
    assert (req.method, req.num_simulations, req.risk_free_rate, req.num_threads) == ("mc_sharpe", 100000, 0.02, None)
    
@pytest.mark.parametrize("field, value", [
    ("method", "max_sharpe"),       # not one of the six names
    ("num_threads", 4),             # the engine only tells 1 apart from "all cores"
    ("num_simulations", 0),
    ("num_simulations", 1_000_001),
    ("symbols", []),
])

def test_optimize_request_rejects(field, value):
    with pytest.raises(ValidationError): _optimize_request(**{field: value})
    
def test_optimize_methods_match_worker():
    # The gateway cannot import services.tasks (it loads the C++ module), so the
    # six names live in two places. Read the worker's table without importing it.
    tree = ast.parse(Path(gateway.__file__).with_name("tasks.py").read_text())
    table = next(ast.literal_eval(node.value) for node in ast.walk(tree)
                 if isinstance(node, ast.Assign)
                 and any(getattr(t, "id", None) == "_CLOSE_FORM_METHODS" for t in node.targets))
    assert set(typing.get_args(gateway.OptimizeMethod)) == {"mc_sharpe", *table}
    # Two names mapped to one Optimizer method means one of them runs the wrong optimizer.
    assert len(set(table.values())) == len(table)
    
def test_submit_optimize_sends_args_in_task_order(monkeypatch):
    sent = {}
    class FakeResult: id = "fake-id"
    def fake_send_task(name, args=None, **options):
        sent.update(name=name, args=args, options=options)
        return FakeResult()
    monkeypatch.setattr(gateway.celery_client, "send_task", fake_send_task)
    out = gateway.submit_optimize(_optimize_request(start="2021-07-01", method="max_sharpe_analytic"))
    assert out == {"job_id": "fake-id", "state": "PENDING"}
    assert sent == {
        "name": "run_optimize_job",
        # Must match run_optimize_job(symbols, start, end, method, num_simulations, risk_free_rate, num_threads).
        "args": [["SPY", "AAPL", "MSFT"], "2021-07-01", None, "max_sharpe_analytic", 100000, 0.02, None],
        "options": {},
    }
    
def test_submit_wf_select_returns_job_id(monkeypatch):
    class FakeResult: id = "fake-id"
    monkeypatch.setattr(gateway, "chord", lambda header, app: lambda callback: FakeResult())
    req = gateway.WfSelectRequest(symbols=["SPY"], start="2021-07-07", end="2026-07-07")
    assert gateway.submit_wf_select(req) == {"job_id": "fake-id", "state": "PENDING", "num_windows": 8}
    
@pytest.mark.parametrize("model, fields", [
    (gateway.JobRequest, {}),
    (gateway.WalkforwardRequest, {"start": "2021-07-07", "end": "2026-07-07"}),
    (gateway.WfSelectRequest, {"start": "2021-07-07", "end": "2026-07-07"}),
])

def test_requests_reject_empty_symbols(model, fields):
    # An empty list used to reach the worker and fail there as a job error.
    with pytest.raises(ValidationError): model(symbols=[], **fields)
    
def test_wf_select_rejects_empty_candidates():
    with pytest.raises(ValidationError):
        gateway.WfSelectRequest(symbol=["SPY"], start="2021-07-07", end="2026-07-07", candidates=[])