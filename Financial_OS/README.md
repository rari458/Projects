# ⚡ Financial OS

**A polyglot quant trading / derivative-pricing platform** — C++20 core, Python orchestration layer, Rust live-data feeder. Built as a deep engineering exercise (not a "beat the market" pitch): a 6-phase refactor covering testing discipline, architecture decomposition, cross-language FFI, parallel compute, a persistence layer, and a distributed task-queue system, each phase verified by build + tests + preserved golden values before moving to the next.

![C++](https://img.shields.io/badge/C++-20-blue)
![Python](https://img.shields.io/badge/Python-3.9%2B-yellow)
![Rust](https://img.shields.io/badge/Rust-2024-orange)
![Tests](https://img.shields.io/badge/gtest-16%20passing-brightgreen)
![Tests](https://img.shields.io/badge/pytest-47%20passing-brightgreen)

## What this is

- **C++20 core** (`src/`, `include/`) — event-driven backtester, **29 registered trading strategies** (technical/stat-arb, options/market-making, execution algos, multi-event "suites"), option pricing (Black-Scholes, Binomial Tree, Monte Carlo + variance reduction), portfolio optimization (Monte Carlo, closed-form tangency, Ledoit-Wolf/Bayes-Stein shrinkage). Built as both a static library and a pybind11 module.
- **Python layer** (repo root, `server/`, `services/`, `research/`) — orchestration only, never reimplements engine logic. REST APIs (a synchronous legacy one and an async distributed one), a Streamlit dashboard, data ingestion, demo/validation scripts.
- **Rust feeder** (`market_data_feeder/`) — live market-data process: Binance L2 WebSocket → order-book imbalance → feeds the C++ engine directly over a C-ABI FFI boundary.

## Architecture

```mermaid
flowchart LR
    subgraph Rust["Rust Feeder"]
        WS[Binance L2 WebSocket] --> OBI[Order Book / OBI]
    end

    subgraph CPP["C++20 Core (src/, include/)"]
        BT[Backtester]
        STRAT[29 Strategies]
        PRICE[Pricing: BS / Tree / MC]
        OPT[Optimizer: MC / Analytic / Shrinkage]
        BT --- STRAT
        BT --- PRICE
        BT --- OPT
    end

    OBI -->|C ABI FFI| BT

    subgraph PyCore["Python Orchestration"]
        PB[pybind11 module: FinancialEngine]
        API[server/main.py — sync REST]
        DASH[dashboard.py — Streamlit]
        DS[data_store.py]
    end

    PB <-.-> BT
    API --> PB
    DASH --> PB
    DS <-->|Postgres| PB

    subgraph Dist["Phase 6: Distributed (Celery + Redis; Docker Compose or Kubernetes)"]
        GW[FastAPI Gateway<br/>services/gateway.py]
        RQ[(Redis Broker)]
        WK1[C++ Worker]
        WK2[C++ Worker]
        WK3[C++ Worker …N]
        DB[(Postgres)]
        GW --> RQ --> WK1 & WK2 & WK3
        WK1 & WK2 & WK3 --> PB
        WK1 & WK2 & WK3 --> DB
    end
```

## Engineering highlights (measured, not claimed)

| # | Finding | Numbers |
|---|---|---|
| 1 | Backtester hot loop was `O(n²)` (`get_max_drawdown()` rescanned the whole equity curve every tick) — fixed to incremental `O(1)` bookkeeping | 42.9ms → 2.6ms @ 10k bars (**16x**); 1k→10k scaling: 64x → 11x |
| 2 | Parallelized the Optimizer's Monte Carlo loop (map-reduce over a static thread pool, `thread_local` RNG per worker) | **~3.3x** @ 100k trials on an 8-physical-core/16-logical machine — learned to trust wall-clock over `items/sec`, and physical cores over logical |
| 3 | Reproduced DeMiguel et al. (2009) "1/N" result on this engine's own walk-forward harness: closed-form tangency, Ledoit-Wolf Σ-shrinkage, and Bayes-Stein μ-shrinkage all tested OOS | OOS Sharpe: **1/N 1.167** > MC-search 1.106 > min-variance 1.050 ≫ raw tangency 0.073 (440% annualized vol) — every μ-using optimizer lost to naive equal-weight out-of-sample |
| 4 | Distributed the walk-forward evaluation itself via a Celery chord fan-out across a replicated C++ worker pool | worker=1 → **1.183s**, worker=3 → **0.491s** (**2.41x**) on a 42-window job; linear-fit decomposition: ~145ms fixed chord overhead + ~24.7ms/task broker round-trip — the system is currently **orchestration-bound, not compute-bound** (engine compute itself is sub-millisecond) |
| 5 | Translated the Docker Compose stack to Kubernetes (Deployments/Services/HPA for redis+gateway+worker, `k8s/financial-os.yaml`) on a single-node cluster | Verified byte-identical behavior end-to-end through `kubectl port-forward` — same gateway → Redis → 3-replica worker pool → DuckDB path, `SUCCESS` state with matching engine output; surfaced a real constraint (DuckDB's embedded single-file model only tolerates a `hostPath` mount on a single node) that traces back to the Phase 5 storage choice |
| 6 | Instrumented the distributed pool with Prometheus + a provisioned Grafana dashboard (`observability/`) — per-replica task counters, a task-duration histogram, and Redis queue depth | Confirmed the scale-out is real *per replica*: a 60-task job split **20 / 20 / 20** across three `instance` labels (only visible because `dns_sd_configs` enumerates every replica — `static_configs` silently merges them). Corrected highlight #4's own number: in-worker execution is **16.8 ms/task**, not the 24.7 ms a two-point fit had attributed to broker overhead. Queue depth peaked at **783** and drained inside one 5s scrape |

See [`ENGINEERING_DECISIONS.md`](./ENGINEERING_DECISIONS.md) for the full story behind each of these — what was assumed, what was measured, and why.

## Repository layout

```
src/, include/        C++20 core — Backtester, Strategy.h (strategy + event catalog), pricing/MC machinery, Optimizer, Bindings.cpp (pybind11 surface)
tests/, benchmarks/    GoogleTest (16 cases) + Google Benchmark
services/              Phase 6 distributed stack: celery_app.py, tasks.py, gateway.py, metrics.py, Dockerfile.{worker,gateway}, tests/ (pytest, 30 cases)
server/                Legacy synchronous FastAPI monolith (data-by-value)
market_data_feeder/    Rust live feeder (Binance L2 → OBI → C++ FFI)
data_store.py          Postgres persistence layer via psycopg 3 (pure, no C++ import — testable standalone)
pytests/               pytest suite for data_store.py (17 cases, against a real Postgres + monkeypatched yfinance)
docker-compose.yml     redis + gateway + horizontally-scalable worker pool
k8s/                   Kubernetes manifests (redis/gateway/worker Deployments+Services, worker HPA) — alternate deployment target to docker-compose
observability/         prometheus.yml + Grafana provisioning (datasource, dashboard provider, financial-os.json) — all config-as-code, no UI state
services/metrics.py    Worker-side Prometheus exporter (Celery signals → task counter + duration histogram on :9100)
```

## Build & run

```bash
# C++ core + Python module (fetches googletest/fmt/pybind11/eigen via CMake FetchContent)
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
ctest --test-dir build                # 16 GoogleTest cases

# Python module: editable scikit-build-core install into the venv (editable.rebuild = true),
# so importing FinancialEngine rebuilds it in build/<wheel_tag>/ after C++ changes
pip install scikit-build-core
pip install --no-build-isolation -e .
# Python dependencies, pinned by constraints.txt to the versions everything is tested with
# (the Docker images and CI install against the same file)
pip install -c constraints.txt "psycopg[binary]" pandas yfinance "celery[redis]" fastapi uvicorn \
    prometheus-fastapi-instrumentator prometheus-client pytest

# Python entry points (run from repo root). data_store connects to FOS_DATABASE_URL, by default
# the Compose postgres service on localhost:5433 (5432 may belong to a native Postgres),
# so start it first: docker compose up -d postgres
python server/main.py                 # legacy sync REST API on :8000
streamlit run dashboard.py
pytest                                 # 47 pytest cases (scoped via testpaths in pyproject.toml);
                                       # the data_store tests use their own fos_test database

# Distributed stack (Phase 6) -- Docker Compose
docker compose up -d --build
python migrate_duckdb_to_postgres.py  # one-off: copies data/market.duckdb into Postgres and
                                      # checks every row (needs duckdb in the venv)
docker compose up -d --scale worker=3 # horizontal scale-out, byte-identical to the monolith

# Observability (comes up with the stack above)
# Prometheus  http://localhost:9090  — targets: gateway, redis_exporter, one per worker replica
# Grafana     http://localhost:3000  (admin/admin) — dashboard is provisioned, not created by hand:
#             /d/financial-os/financial-os-distributed-workers
# Note: Grafana's DB lives in the container layer by design (no volume), so provisioning stays
#       idempotent. Recreate rather than restart after changing observability/ config.

# ...or the same stack on Kubernetes (verified on a 2-node minikube; see decision #15)
docker tag financial_os-worker:latest financial-os-worker:latest   # Compose builds the images
docker tag financial_os-gateway:latest financial-os-gateway:latest
minikube image load financial-os-worker:latest financial-os-gateway:latest
kubectl apply -f k8s/financial-os.yaml
kubectl get pods -n financial-os -o wide -w
kubectl -n financial-os port-forward pod/postgres-0 5434:5432 &    # then, once:
python migrate_duckdb_to_postgres.py --dsn postgresql://fos:fos@localhost:5434/market
kubectl -n financial-os port-forward svc/gateway 8002:8001 &       # gateway on :8002

# Live microstructure feed: one process, Rust drives the C++ engine over the C ABI
# (links build/src/libfinancial_engine_c.so, so run the CMake build above first)
cargo run --manifest-path market_data_feeder/Cargo.toml
```

## Testing

16 GoogleTest cases (`ctest --test-dir build`), including 5 **characterization / golden-master** tests (`tests/BacktesterCharacterizationTest.cpp`) that pin the Backtester's exact numeric output — 2 price-path strategies (MACD, EMA) and 3 event-driven suites (META_BRAIN, STRUCTURAL_ARB, GLOBAL_MACRO) — so any unintended behavior change during refactoring shows up as a failing test, without asserting the behavior is "correct."

The Python layer has a 47-case pytest suite (`pytest`, scoped via `testpaths` in `pyproject.toml` to `services/tests/` + `pytests/` so it never collides with the root-level `*_test.py` demo scripts, which match pytest's default discovery patterns but are not pytest):
- `services/tests/test_gateway.py` (27 cases) — `_add_months`, `_walkforward_windows`, `_wf_train_test_windows`: the date-window math behind the walk-forward endpoints, and the exact spot where hand-typed bugs (singular/plural `window`/`windows`, a missing leading underscore) turned up earlier in development. Several cases are pinned directly against live-verified runs (19 / 7 / 42 windows). Nine more cover `/optimize`: request validation (defaults, an unknown method, `num_threads` other than 0/1, out-of-range `num_simulations`, an empty symbol list); a check that the gateway's method names match the worker's table in `tasks.py`, read through `ast` so the C++ module is never imported; and stubbed `send_task`/`chord` calls that pin `run_optimize_job`'s argument order and the `/wf_select` response. Each of the four hand-typed bugs found while building the optimize job, put back one at a time, fails at least one of them. Four more check that `/jobs`, `/walkforward` and `/wf_select` reject an empty symbol list, and `/wf_select` an empty candidate list, with a 422 at the gateway instead of a job that fails in the worker. Four more cover `/ingest`: it goes to the `ingest` queue that only the ingester consumes, it rejects an empty symbol list and an unknown period, and every task name the gateway dispatches (through `send_task` or `signature`, read with `ast`) is defined in `tasks.py`, since a misspelled name leaves a job in `PENDING` with no error anywhere.
- `services/tests/test_metrics.py` (3 cases) — the worker's task counter records each finished attempt under its own `status` label: `success`, `retry` and `failure`. A retry used to be counted as a failure, which overstated failures during lock conflicts (see decision #14).
- `pytests/test_data_store.py` (17 cases) — the Postgres persistence layer, against a real Postgres (the Compose service locally, a service container in CI) in its own `fos_test` database. Without a reachable server these tests error rather than skip, so they can never pass without running. They cover schema creation, `get_ohlc`/`symbols`/`get_returns_matrix` round-trips, `get_aligned_ohlc` keeping only the dates every symbol has, and `ingest_symbols` with `yf.download` monkeypatched: MultiIndex flattening, a symbol with no data reported as failed, counts of rows actually added, partial-failure partitioning, an ingest that fails halfway leaving nothing behind, a reader that neither waits for nor sees an uncommitted ingest, and a read-only connection refusing writes.

The Celery task/worker glue itself is still verified by manual/curl + Docker Compose round-trips rather than integration tests — a known, smaller remaining gap.

## The 6-phase engineering roadmap

| Phase | Focus | Key result |
|---|---|---|
| 1 | Safety net | Golden-master characterization tests, CI, `.clang-format`/`.clang-tidy`, CMake presets |
| 2 | Architecture | Self-registering `StrategyFactory`; decomposed the `Backtester` god-class (`EquityCurve`/`DataHandler`/`Portfolio`); unified 12 event-handler virtuals into one `on_event(std::variant<...>)` |
| 3 | Cross-language + performance | Rust↔C++ C-ABI FFI; Google Benchmark surfaced the `O(n²)` bug (see highlight #1); packaged as an editable-installable pybind11 wheel (scikit-build-core) |
| 4 | Parallel compute | Thread-pooled Monte Carlo optimizer (see highlight #2) |
| 5 | Data + quant research | DuckDB persistence layer; an optimizer-method research arc (MC → closed-form tangency → walk-forward OOS collapse → Ledoit-Wolf → Bayes-Stein) concluding with a reproduction of the "1/N beats MVO" result (see highlight #3) |
| 6 | Distributed systems | Celery + Redis + Docker Compose: async gateway → broker → horizontally-scalable C++ worker pool → by-reference DuckDB; a Celery-chord fan-out for distributed walk-forward (fixed-strategy and adaptive in-sample strategy selection); measured scale-out speedup (see highlight #4); hardening (task-loss-safe acks, targeted retries, health-checked startup ordering, graceful shutdown) |

All 6 phases are complete as of 2026-07-09.

## Beyond the roadmap: further expansion (in progress)

| Item | Status | Notes |
|---|---|---|
| Kubernetes deployment | ✅ done | `k8s/financial-os.yaml` — Deployments/Services/HPA for redis+gateway+worker on a single-node cluster, verified end-to-end (see highlight #5) |
| Observability (Prometheus/Grafana) | ✅ done | `observability/` — worker-side exporter on `worker_ready`, `dns_sd_configs` per-replica scraping, `redis_exporter` queue depth, and a provisioned 4-panel dashboard (see highlight #6) |
| `optimize` distributed job type | ✅ done | `POST /optimize` → `run_optimize_job`: Monte Carlo max-Sharpe or one of five closed-form methods (inverse volatility, minimum variance, analytic / shrunk / robust max-Sharpe) on the returns matrix from the read-only DuckDB mount. Verified through the Compose stack: the analytic weights match a local run of the same task exactly. `num_threads` is limited to 0 or 1 because the engine treats it as a switch between one thread and a `hardware_concurrency()` pool. A request that leaves it out gets the worker's `FOS_OPTIMIZE_THREADS`: `0` on Compose, where the pool was 1.36–2.17x faster at 1–8 replicas, and `1` on k8s, where the 1-CPU limit leaves the pool nothing to run on (decision #13) |
| Write-side ingestion service | ✅ done | `POST /ingest` → `ingest_symbols` on its own `ingest` queue, consumed only by a single `ingester` container with a read-write mount of `data/`. It never writes the live file: `data_store.ingest_snapshot` writes a copy and swaps it in with `os.replace`, because DuckDB will not let a writer and the workers' readers open the file at the same time. Measured with `benchmarks/ingest_under_load.py` (3 workers, 2000 backtests per run): 15 swaps during a run left all 2000 jobs successful with zero retries, while holding an in-place write lock for 5 s at a time failed 1571 of 2000 (see decision #14). Since replaced by Postgres (next row) |
| Postgres in place of DuckDB | ✅ done (decision #15) | `data_store.py` on psycopg 3 against a `postgres:18-alpine` Compose service. An ingest is one transaction, so readers see all of it or none and never wait, which removes the copy-and-swap, the lock file and the `data/` mounts. `migrate_duckdb_to_postgres.py` copied all 34,166 rows and compared them row by row, and the reference 3-symbol MACD backtest returns the same 1255 bars, 34 trades and final equity. Under the same load as decision #14 (3 workers, 2000 backtests per run), a write transaction held open for 5 s failed none of the jobs (DuckDB: 1571 of 2000) and left throughput at 112 jobs/s against a 113 baseline; only an `ACCESS EXCLUSIVE` table lock slowed readers, who then waited rather than failed. On Kubernetes, Postgres runs as a StatefulSet with a persistent volume and its credentials in a Secret. On a 2-node minikube, workers on both nodes and an ingester on the node without the database all reached it over the network (100 / 101 / 101 backtests per worker, the reference result unchanged), which lifts the single-node limit of decision #11. Caveat found there: minikube's default storage class does not tie the volume to its node, so a Postgres pod forced onto the other node started an empty database (see decision #15) |
| Large-universe stress test | planned | push distributed walk-forward further to see the C++ engine itself, not orchestration, become the bottleneck |
| CI for the `services/` Docker stack | planned (last) | no longer blocked: `.github/workflows/financial_os.yml` at the git root now runs the gcc C++ build with ctest, the Rust feeder (fmt, clippy, FFI round-trip test) and pytest on every change under `Financial_OS/`. Still missing: building the Compose images and a smoke job through the gateway. clang is left out of the matrix until fmt moves past 10.2.1 and the `-flto=auto` static library links under clang |
