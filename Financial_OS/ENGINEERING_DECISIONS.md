# Engineering Decisions

This document records *why*, not just *what*. Each entry captures a question that came up during the 6-phase refactor, what was assumed going in, what was actually measured, and the decision that followed. The throughline across almost all of them: **measure, don't assume.**

---

## 1. Refactoring uncovered a live wiring bug (Phase 2)

**Context:** Collapsing 12 separate `on_*_event` virtuals into a single `on_event(const Event&)` dispatch (`Event = std::variant<...>`), and the matching 12 `send_*_event` methods into one `send_event`.

**Assumption:** This was framed as a pure refactor — same behavior, cleaner dispatch, no functional change expected.

**What turned up:** While rewiring the pybind11 bindings for the unified `send_event`, `send_alt_data` was found wired to `send_anomaly_event` — a pre-existing, silent binding bug that had nothing to do with the refactor itself. It only surfaced because the refactor forced every event path to be re-examined line by line.

**Why it matters:** A disciplined refactor with a safety net (golden-master characterization tests already in place from Phase 1) doesn't just make code cleaner — it's a bug-finding tool. Also fixed 3 redundant `dynamic_cast`s in the same pass.

---

## 2. The Backtester's hidden O(n²) (Phase 3)

**Context:** Benchmarking the `on_market_data` hot loop with Google Benchmark after adding the C++/Rust FFI boundary.

**Assumption:** The MACD strategy's per-tick cost should be flat — nothing in the strategy logic looked like it scaled with history length.

**What was measured:** `check_risk_limits` called `get_max_drawdown()` on every single tick, and `get_max_drawdown()` did a full `O(n)` rescan of the equity curve every time (`Analytics::CalculateMaxDrawdown`). Scaling from 1k to 10k bars cost **64x**, not the expected ~10x — the signature of a hidden quadratic term.

**The fix:** Made `EquityCurve` track running peak + max-drawdown incrementally on every `record()` call — `O(1)` per tick, bit-identical output to the batch version (all 16 golden tests stayed green).

**Result:** 10k-bar MACD backtest: **42.9ms → 2.6ms (16x)**; the 1k→10k scaling factor dropped from 64x to 11x (quadratic → linear).

**Why it matters:** This bug was invisible from reading the code — `get_max_drawdown()` looked like an innocuous getter. It only became visible under a benchmark that varied input size and looked at scaling behavior, not just absolute time.

---

## 3. Threads that made things slower (Phase 4)

**Context:** Parallelizing the Optimizer's Monte Carlo loop (independent random-portfolio trials) with a thread pool (BS::thread_pool).

**Assumption:** Wrapping the trial loop in a thread pool should just make it faster.

**What was measured (first attempt):** Constructing the thread pool *inside* the function — spawning and joining ~16 OS threads on every call — made the parallel path **slower** than serial at 10k trials (4.07ms vs 1.76ms serial).

**The fix:** Moved the pool to a function-local `static`, reused across calls. Result: **~2.2x @ 10k, ~3.3x @ 100k** vs serial.

**A second hypothesis, disproven:** Suspecting per-trial heap allocation was next in line, removed it (thread-local reused buffers, a flat pre-allocated weights matrix instead of a vector of structs). This bought only ~4% and left *serial* time unchanged too — meaning glibc's malloc was already using per-thread arenas, so small allocations were never hitting a global lock. The fix that mattered was thread *lifecycle*, not allocation.

**Why it matters:** Two plausible performance hypotheses, both testable, both measured before committing to either — one was right, one wasn't, and the numbers said which.

---

## 4. Physical vs. logical cores (Phase 4)

**Context:** Same Optimizer parallelization — after fixing thread-pool lifecycle, expected near-linear scaling with thread count on a "16-thread" machine.

**Assumption:** ~16x speedup on a 16-thread machine.

**What was measured:** ~3.3x at 100k trials. The Google Benchmark cache report (`L1/L2 (x8)`) showed the machine has **8 physical cores with hyperthreading (16 logical)** — compute-bound work scales with physical cores, not logical ones, and all-core clock speed runs below single-core turbo. Combined with per-call submit/barrier coordination overhead, 3.3x is the *correct* answer for this hardware, not a bug.

**A separate measurement gotcha:** In this specific benchmark, Google Benchmark's `CPU` and `items_per_second` columns measure the *waiting main thread*, making serial execution look faster than parallel by that metric — only wall-clock `Time` is trustworthy for a thread-pool benchmark like this one.

**Why it matters:** Naive "N cores = Nx speedup" is a common junior mistake. Knowing to check *which* number the benchmark tool is actually reporting, and physical-vs-logical topology, turned a "why isn't this scaling" panic into an expected, explainable result.

---

## 5. The optimizer that looked brilliant and blew up out-of-sample (Phase 5)

**Context:** Building a closed-form tangency-portfolio optimizer (`w ∝ Σ⁻¹(μ − r_f·1)`) to replace a Monte Carlo search that degraded in high dimensions (26-asset MC search barely explored the simplex, returned near-flat weights).

**Assumption:** A closed-form solution should be strictly better than a randomized search.

**What was measured in-sample:** Analytic tangency Sharpe **2.44** vs. Monte Carlo's **1.12** — a huge apparent win. But the analytic portfolio carried **2525% gross exposure, 25x effective leverage, and 8 short positions** — the textbook signature of Markowitz's "estimation-error maximizer" pathology (Σ⁻¹ amplifies noise in near-collinear equity return directions).

**The real test — walk-forward out-of-sample (weights fixed from in-sample only, no lookahead), 15 rolling windows:** OOS Sharpe **Equal-weight 1.167 > Monte Carlo 1.106 > Min-variance 1.050 ≫ raw Tangency 0.073** (440% annualized volatility — the 2.44 in-sample Sharpe had collapsed almost entirely). This reproduces DeMiguel et al. (2009)'s well-known "1/N" result, on this engine's own code and data.

**Why it matters:** In-sample optimality is not the same question as out-of-sample performance. The naive 1/N portfolio — the one requiring *no* estimation at all — beat every optimizer that used estimated expected returns. This is the single strongest evidence in the whole project that "more sophisticated" and "better" are different axes.

---

## 6. Shrinkage: an honest miss (Phase 5)

**Context:** Following up the tangency-portfolio blowup with Ledoit-Wolf (2004) covariance shrinkage and Jorion (1986) Bayes-Stein mean shrinkage, to see whether shrinkage could rescue the optimizer.

**Prediction made before running the experiment:** annualized volatility should fall from 440% to somewhere around 15–25%.

**What was measured:** Σ-shrinkage alone (Ledoit-Wolf): Sharpe 0.094, vol 268% (440%→268% = 1.6x reduction). Adding μ-shrinkage (Bayes-Stein): Sharpe 0.099, vol **79%** (268%→79% = 3.4x reduction) — better, but nowhere near the 15–25% predicted, and still far below 1/N's Sharpe of 1.167.

**What this shows:** μ-shrinkage helped substantially more than Σ-shrinkage, confirming that expected-return estimation is the bigger error source (consistent with the min-variance result, which drops μ entirely). But the miss on the vol prediction is itself informative — identity-target Ledoit-Wolf under-shrinks correlated equities, which in turn weakens how much Bayes-Stein's shrinkage factor can pull toward the grand mean. A market-factor shrinkage target or hard leverage constraints would likely do more.

**Why it matters:** Stating a falsifiable prediction before running the experiment — and reporting the miss plainly instead of reframing the result after the fact — is what makes the win in story #5 credible in the first place.

---

## 7. Why the distributed worker pool uses `--pool=solo` (Phase 6)

**Context:** Choosing a Celery worker concurrency model for a worker process that has a compiled C++ extension (pybind11) loaded in it.

**The two alternatives considered, and why each was rejected:**
- **`--pool=prefork`** (Celery's default): forks the worker process to create children. This codebase has (a) self-registering static objects (`StrategyRegistrar`) and (b) Phase 4 introduced function-local `static BS::thread_pool` instances that spawn real OS threads. `fork()` only carries the calling thread into the child — if a pool were constructed *before* a fork (e.g., after the first Optimizer call in that worker), the child would inherit the pool's mutex/object state with no live worker threads behind it: a deadlock waiting to happen.
- **`--pool=threads --concurrency=N`**: no forking, but `Bindings.cpp` never calls `py::call_guard<py::gil_scoped_release>()`, so every C++ engine call holds Python's GIL. A Python thread pool here would only interleave during I/O waits (Redis round-trips, DuckDB reads) — not actually parallelize the C++ compute.

**The decision:** `--pool=solo` (one task at a time, no forking, no threading) inside each container, scaling out by **replicating containers** instead — true OS-level parallelism (separate processes, separate GILs, separate address spaces), with zero fork- or GIL-related hazard. Slice 2-C measured this delivering a real 2.41x at `--scale worker=3`.

**Why it matters:** The "right" concurrency primitive isn't a Celery-specific choice in isolation — it falls directly out of a decision made two phases earlier (Phase 4's thread pools) and a binding detail (the GIL not being released). Systems decisions compound across a project; the two aren't discoverable in isolation.

---

## 8. A crash that taught the queue to heal itself (Phase 6)

**Context:** While iterating on a distributed walk-forward endpoint, a hand-typed bug (a stray trailing `.` instead of `,` in a task's return dict) caused a `SyntaxError` at worker import time.

**What happened:** The worker container crash-looped (`Exited` / `Restarting`), never fully starting. A job submitted to the queue during this window sat in `PENDING` state **forever** — the API surface showed nothing wrong; the only way to see the real cause was `docker compose ps` (worker `Exited`) plus `docker logs <worker>` for the traceback.

**The follow-up question this raised:** even *without* a crash-loop, what happens if a worker dies mid-task (OOM-killed, `docker stop`, a bad deploy)? By default, Celery acknowledges a task as soon as it's received, not when it finishes — so a task in flight when its worker dies is silently **lost**, not retried.

**The fix:** `task_acks_late=True` (ack only after the task completes) + `task_reject_on_worker_lost=True` (explicit requeue on a lost connection) + `worker_prefetch_multiplier=1` (so one worker can't hoard several unacked tasks, delaying their redelivery to workers that are still alive).

**Why it matters:** The specific bug that triggered this (a typo) wasn't the real finding — the real finding was that the *system's* default failure mode (early ack) would have silently dropped work under a broader class of failures than just this one typo. Verified safe via regression only: with tasks completing in ~25ms, timing a manual `docker kill` into the execution window isn't practically achievable by hand, so this was verified as "correct per documented Celery semantics + zero happy-path regression" rather than via a live fault injection.

---

## 9. The speedup that wasn't there — until the ruler was fine enough (Phase 6, Slice 2-C)

**Context:** Measuring the wall-clock speedup of scaling the worker pool from 1 to 3 replicas on a distributed walk-forward job.

**First measurement:** worker=1 and worker=3 both reported `real ≈ 1.1s` on the same request. This looked like *zero* speedup.

**What was actually going on:** The request (7 windows × 7 backtests each = 49 C++ engine calls on a few hundred bars of daily data) completes in well under a second of actual compute — the polling loop's 1-second sleep interval was the thing being measured, not the job.

**The fix:** Grew the workload (`step_months=1` → 42 windows on the same 5 years of data → 294 backtest calls) and tightened the poll interval to 0.2s. **Now:** worker=1 → 1.183s, worker=3 → 0.491s — a real **2.41x**.

**Going one step further:** fitting `T(n_tasks) = F + n_tasks·t` from the two data points (42 tasks / 14 tasks, since 42÷3 divides evenly) solved exactly: **F ≈ 145ms** fixed overhead (chord setup, callback task, first poll round-trip) that does *not* shrink with more workers, **t ≈ 24.7ms/task** — almost entirely Celery/Redis dispatch and serialization, not C++ compute (which Phase 3/4 benchmarks already show is sub-millisecond for a job this size). The theoretical max from the round-count ratio alone (42÷14) was 3x; the measured 2.41x is exactly the shortfall Amdahl's law predicts from that fixed `F`.

**Why it matters:** The first, "no speedup" measurement was wrong — not because the system doesn't scale, but because the measuring instrument's resolution (1-second polling) was coarser than the thing being measured. The real, useful finding underneath — that this system is currently *orchestration-bound*, not *compute-bound* — would have been invisible without going back and fixing the ruler first.
