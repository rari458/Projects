# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Working conventions

- **All editing is done by the user.** Do not modify files directly; propose changes and let the user apply them.
- **All annotations must be written in English** (comments, docstrings, commit messages, and other in-code notes).

## What this is

A polyglot quant trading / derivative-pricing platform ("Financial OS" / "Aladdin-Killer"). Three languages, one data flow:

- **C++20 core** (`src/`, `include/`) — all compute: event-driven backtester, 30+ trading strategies, option pricing, portfolio optimization. Built as a static lib *and* a pybind11 module.
- **Python layer** (repo root, `server/`, `research/`) — orchestration only. Imports the compiled C++ module and drives it: REST API, Streamlit dashboard, data ingestion, demo/validation scripts.
- **Rust feeder** (`market_data_feeder/`) — standalone live market-data process: Binance L2 WebSocket → order-book imbalance → UDP blast to `127.0.0.1:9999`.

## The C++/Python bridge (read this first)

Python never reimplements logic — it calls into the C++ module. The pybind11 target `FinancialEnginePy` is renamed at build time to output `FinancialEngine`, landing in `build/src/FinancialEngine*.so`.

Every Python entry point starts with `sys.path.append('./build/src')` (relative to CWD) and `import FinancialEngine`. Consequences:

- **You must build the C++ project before any Python code will run.** A stale or missing `.so` is the cause of nearly all `ImportError: FinancialEngine` failures.
- **Run Python scripts from the repo root**, since the module path is relative.
- After changing any C++ source or `Bindings.cpp`, rebuild before re-running Python.

## Build & test

```bash
# Configure + build (fetches googletest, fmt, pybind11, eigen via CMake FetchContent — first run is slow)
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build

# C++ unit tests (GoogleTest)
ctest --test-dir build                  # all tests
./build/tests/UnitTests                 # run the test binary directly
./build/tests/UnitTests --gtest_filter=GreeksTest.*   # single test / suite
```

The C++ lib builds with `-Wall -Wextra -Werror` (MSVC: `/W4 /WX`) plus `-flto=auto`. **Warnings are build failures** — keep new code warning-clean. C++20 is required (`CMAKE_CXX_EXTENSIONS OFF`).

Build targets (from `src/CMakeLists.txt`):
- `FinancialEngine` — static library (all of `src/*.cpp` except `main.cpp`/`Bindings.cpp`)
- `FinancialOS` — native C++ executable from `main.cpp`
- `FinancialEnginePy` — the Python module (output name `FinancialEngine`)

When adding a new `.cpp` to the core, register it in the `SOURCES` list in `src/CMakeLists.txt`; new gtest files go in `tests/CMakeLists.txt`.

## Running the system

```bash
python server/main.py            # FastAPI REST API on :8000 (/api/backtest, /optimize, /evolve, /scan, /regime)
streamlit run dashboard.py       # Streamlit control panel
python data_pipeline.py          # yfinance → C++ engine demo

# Live microstructure pipeline (two processes):
cargo run --manifest-path market_data_feeder/Cargo.toml   # Rust feeder → UDP :9999
python live_stream_udp.py                                 # listens on :9999, feeds C++ engine
```

The many root-level `*_test.py` / `test_*.py` files are **standalone demo/validation scripts, not pytest** — run each with `python <file>.py`. They build their own synthetic or yfinance data and print results.

## Architecture

### Backtester is the hub
`Backtester` (`src/Backtester.cpp`, ~74KB; `include/Backtester.h`) is the central event-driven engine. Constructed as `Backtester(initial_capital, strategy_type, leverage)`.

- **Strategy selection is a string → class dispatch** in the constructor (`src/Backtester.cpp` ~line 1344). The `strategy_type` string (`"MACD"`, `"PAIRS"`, `"L3_EXECUTION"`, `"META_BRAIN"`, etc.) maps to a concrete `Strategy` subclass; unknown strings fall back to `EMAStrategy`. To add a strategy: implement it in `Strategy.h`, then add a branch here.
- **Market data in:** `on_market_data(symbol, timestamp, open, high, low, close)`, called tick-by-tick.
- **Higher-level events in:** typed `send_*_event(...)` methods (`send_meta_event`, `send_crypto_event`, `send_macro_event`, `send_l3_message`, …), each taking a matching event struct.
- **Results out:** `get_total_equity`, `get_trade_history`, `get_max_drawdown`, `get_equity_history`, `get_holdings`.
- Multi-asset: maintains per-symbol OHLC vectors and holdings. Has a `RiskManager` (drawdown/VaR limits → liquidation) and optional `RegimeDetector` filter.

### Strategy.h is the strategy + event catalog
`include/Strategy.h` (~19KB) holds the `Strategy` base class, all concrete strategies, and every event `struct` + `enum` (e.g. `MetaBrainType`, `CryptoEventType`, `StructArbType`). Strategies are grouped into "suites" (`EventDrivenSuite`, `MetaBrainSuite`, `L3ExecutionSuite`, …) that each handle a family of `send_*_event` calls.

### Supporting C++ modules
Pricing/math: `BlackScholesFormulas`, `BinomialTree`, `SimpleMC` + Monte Carlo machinery (`Random`, `AntiThetic`, `MCStatistics`, `ConvergenceTable`), `ExoticBSEngine`, `Payoff`/`PayoffFactory` (factory + singleton registration). Quant: `Optimizer` (Sharpe via Monte Carlo, Eigen-backed), `PairSelector`, `RegimeDetector`, `PCAArbitrage`, `OrderBook`, `Analytics`, `KalmanFilter`. Eigen3 is a hard dependency of the core lib.

### Bindings
`src/Bindings.cpp` is the single pybind11 surface — every class, event struct, enum, and free function exposed to Python lives here. Adding a C++ capability that Python needs means editing this file.

### FastAPI gotcha
In `server/main.py`, C++ objects returned to handlers (e.g. `Trade`) **must be manually converted to plain dicts** before being returned, or FastAPI's serializer crashes. Follow the existing `clean_trade_list` pattern when adding endpoints.

### Rust feeder contract
`market_data_feeder/src/main.rs` sends fire-and-forget UDP datagrams of `"best_bid,best_ask,obi"` (formatted floats) to `127.0.0.1:9999`. `live_stream_udp.py` parses that CSV and feeds the C++ engine. Rust uses edition 2024 / tokio.
