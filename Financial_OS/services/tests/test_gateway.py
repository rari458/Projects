# services/tests/test_gateway.py

from datetime import date
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