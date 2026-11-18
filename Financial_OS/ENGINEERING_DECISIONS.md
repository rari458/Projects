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

---

## 10. Writing the first tests surfaced a silent gap in the returns matrix (post-roadmap hardening)

**Context:** Adding the first automated tests for `data_store.py`'s `get_returns_matrix` (the function feeding the Optimizer research arc in stories #5–6) — a pure function with zero prior coverage, tested against an in-memory DuckDB rather than the real yfinance-backed one.

**Assumption:** `pivot(...).dropna()` before `pct_change()` just filters out assets with no history yet (e.g. an IPO), the ordinary reason a cross-sectional row would be incomplete.

**What was measured:** A synthetic edge case — two symbols, one (`MSFT`) missing a single bar in the *middle* of an otherwise-complete 3-day series — showed only 1 return survives from 3 days of data, and that surviving return silently spans day 1 → day 3, not day 2 → day 3. `pivot().dropna()` drops the *entire* cross-sectional row the moment any one symbol is missing that date, before `pct_change()` ever runs — so `pct_change()` can silently skip non-consecutive trading days with no signal that it happened.

**Why it matters:** Invisible on real data for liquid large-caps (which rarely have gaps), but would silently distort computed returns for names with occasional missing bars — trading halts, illiquid tickers, corporate actions — exactly the assets a real universe-mining pipeline would eventually pull in. Caught by writing a synthetic edge-case test, not by reading the code: the same throughline as story #2's `O(n²)` bug — a function that looks correct until you feed it the one input shape nobody tried yet.

---

## 11. Kubernetes surfaced a constraint two phases earlier had already baked in

**Context:** Translating the Phase 6 Docker Compose stack (redis + gateway + worker) into Kubernetes Deployments/Services/HPA on a local single-node minikube cluster, to demonstrate orchestration beyond docker-compose's single-host model.

**What came up:** The worker Deployment needs read access to `market.duckdb`, a simple bind-mount under Compose. Translating that mount to Kubernetes (`hostPath`) exposed a constraint that Phase 5's storage choice — DuckDB, an embedded single-file database, not a client-server one — already implied but had never been tested against: a `hostPath` volume only works correctly if every pod using it is scheduled on the *same node*. On a genuinely multi-node cluster this breaks silently (pods on other nodes simply wouldn't see the file) unless replaced with a ReadWriteMany volume (NFS, cloud filestore) or DuckDB itself were swapped for a client-server database.

**Decision:** kept `hostPath` for this single-node minikube deployment (it matches Compose's own bind-mount semantics most directly) and documented the multi-node limitation explicitly rather than engineering around a scale this project doesn't operate at yet.

**A second, smaller finding:** the worker `HorizontalPodAutoscaler` scales on CPU utilization — the only metric Kubernetes ships out of the box — but these workers are I/O-bound (waiting on the Redis broker and DuckDB reads, not compute; Slice 2-C already measured that per-task Celery/Redis overhead dominates sub-millisecond C++ compute at this data scale). CPU is a weak scaling signal for this workload; the correct one would be queue depth via KEDA + a Redis-based scaler, left as a known follow-up rather than implemented here.

**Why it matters:** A storage decision from Phase 5 (DuckDB for embedded simplicity) and a measurement from Phase 6 (this system is orchestration-bound, not compute-bound) both resurfaced as concrete constraints the moment the deployment target changed. Architecture decisions compound forward in ways invisible until the surrounding infrastructure actually changes — the same lesson as story #7's `--pool=solo` rationale, one infrastructure layer further out.

---

## 12. Instrumentation is the one subsystem whose bugs render as an empty graph (post-roadmap expansion)

**Context:** Adding Prometheus + Grafana to the Phase 6 Compose stack — a worker-side exporter (`services/metrics.py`) started on Celery's `worker_ready` signal, a scrape config, a `redis_exporter` for queue depth, and a provisioned dashboard — so the distributed pool's behavior could be *read* rather than inferred from `curl` timings.

**The scrape-config decision, and the trap under it:** The obvious config is `static_configs: [targets: ["worker:9100"]]`. It is wrong in a way that looks right. Compose resolves `worker` through round-robin DNS to *one* replica per lookup, so Prometheus would scrape a single arbitrary worker and label every sample with the same `instance` — silently merging three replicas' counters into one series. At `--scale worker=1` the output is indistinguishable from correct. `dns_sd_configs` (type `A`, port 9100) instead enumerates every A record as its own target. **Measured:** a 60-task walk-forward split **20 / 20 / 20** across three distinct `instance` labels — the per-replica distribution that `static_configs` would have made unobservable, and the direct visual confirmation of story #7's "scale out by replicating containers" claim.

**The bootstrap problem in histogram buckets:** Prometheus histogram buckets must be chosen *before* any measurement exists, and quantiles can only be interpolated inside a bucket that actually splits the data. The first tuple was centered on story #9's `t ≈ 24.7ms/task`: **59 of 60 samples landed in a single `(0.01, 0.025]` bucket**, making every quantile a meaningless bucket-edge readout. A second pass, still reasoning from #9, put **115 of 118** in `(0.015, 0.025]`. Only after adding boundaries at 12.5 / 15 / 17.5 / 20 / 22.5 ms did the distribution resolve into a usable staircase — cumulative **46 / 55 / 56 / 56 / 57 / 59** across `0.0175 → 0.04`.

**What that measurement then corrected:** in-worker execution time (`task_prerun` → `task_postrun`, which excludes queue wait) averages **16.8 ms**, not 24.7 ms. Story #9 derived 24.7 ms from a two-point linear fit and attributed it "almost entirely" to Celery/Redis dispatch and serialization. The histogram splits that number for the first time: roughly two-thirds of the per-task cost is *inside* the worker — DuckDB reads and Python/pybind11 glue around a sub-millisecond C++ call — and only the remainder is broker round-trip. The two figures come from different sessions and slightly different job shapes, so this is a re-attribution rather than a controlled decomposition, but the direction is not in doubt: #9's fit could not see the split, and assigning the whole of `t` to the broker was an over-read of what a two-point fit supports.

**Four defects in this slice, and what each of them looked like:**
- `services/metrics.py` had `if started is None:` where `is not None` was meant. The counter incremented normally; the histogram silently never recorded a sample. **Symptom: one empty panel.**
- A bucket tuple with `0.075` where `0.0075` was intended is non-monotonic, so `Histogram()` raises at *construction* — i.e. at import, inside a module `celery_app.py` lists in `include`. Every worker container died at startup. **Symptom: workers absent from `docker compose ps`,** with nothing in the metrics stack pointing at metrics as the cause.
- The dashboard queried `celery_task_total`; the metric is `celery_tasks_total`. **Symptom: `No data` — which is exactly what a correct panel shows before any traffic arrives.**
- Grafana refused to start entirely (`Datasource provisioning error: data source not found`) because its SQLite DB, living in the container's writable layer, still held a datasource provisioned earlier *without* a `uid`; adding `uid: prometheus` gave the provisioner a key that matched nothing. `docker compose restart` reuses the container and therefore the DB, so only `rm` + `up` clears it. In the same session Prometheus failed the opposite way — an old container survived a restart but had lost its bind mount to `./observability`, reporting the config file as `no such file or directory` while the file sat plainly on disk. **Restart preserved the state that needed clearing and could not restore the state that needed rebuilding; both wanted recreation.**

**Why it matters:** Every other subsystem in this project announces its own failures — a failing golden-master test, a crash-looping container, a traceback. Instrumentation does not. A metric that is never observed, a series whose replicas are silently merged, a quantile interpolated inside a single bucket, and a panel querying a misspelled metric all render as *a healthy-looking idle system*. Story #9 made the same point about resolution one layer down (a 1-second poll can't measure a sub-second job); this is that lesson generalized — the tooling you build to check your assumptions is itself unchecked, and it is the one subsystem where "looks fine" carries no information at all. The most useful artifact of this slice is not the dashboard but the correction it forced on a number that had already been written down as measured.

**Follow-up this sharpens:** story #11 identified queue depth (KEDA + a Redis scaler) as the correct autoscaling signal for these workers, CPU being a weak proxy. Now measurable: a burst peaked at **783 queued tasks and drained to 0 inside a single 5-second scrape interval**. The signal is the right one, but it lives on the same timescale as the sampling — an autoscaler polling at that rate would frequently observe `0` for a queue that had just been several hundred deep. Scrape/poll interval is a load-bearing parameter of that design, not a detail.

---

## 13. The thread setting belongs to the deployment, not the request (post-roadmap expansion)

**Context:** The `optimize` job (`POST /optimize` → `run_optimize_job`) is the first task in the distributed stack where C++ compute outweighs orchestration, at least for a large universe. With all 26 symbols and 100k Monte Carlo trials it spends about 106 ms inside the worker on one thread, against story #12's 16.8 ms backtest tasks. At 3 symbols the same task takes about 8 ms. The request's `num_threads` is passed straight to the Optimizer's switch from stories #3–4: `1` runs on one thread, and anything else uses the static `hardware_concurrency()` pool, 16 threads on this 8-core / 16-thread host. Story #7 already scales the stack by replicating containers. The open question was whether each replica still gains from its own pool once several replicas share the same 8 physical cores, or whether the two kinds of parallelism get in each other's way. Eight replicas with 16 threads each means 128 threads on 8 cores, so a crossover somewhere below 8 replicas seemed plausible.

**How it was measured:** `benchmarks/optimize_scaling.py` submits 24 warm-up jobs, then 120 identical jobs at once (26 symbols, 100k trials, from 2021-07-01). It waits for them in order with a 20 ms poll, because story #9 showed the poll interval must be finer than the job. It reads the in-worker mean from the deltas of the Prometheus histogram's `_sum` and `_count`. A mean computed that way is exact whatever the buckets are, so story #12's bucket problem does not touch it. The matrix covered 1, 3 and 8 replicas with `num_threads` 0 and 1, on Docker Compose with no CPU limits, run three times. Medians, with the min–max range in brackets:

| replicas | `num_threads=1` jobs/s | `num_threads=0` jobs/s | 0 ÷ 1 (worst pairing) | in-worker ms, 1 / 0 |
|---|---|---|---|---|
| 1 | 9.3 (9.3–9.4) | 20.2 (18.8–20.4) | **2.17x** (2.00x) | 105.6 / 48.1 |
| 3 | 26.5 (26.4–26.6) | 46.1 (41.8–46.3) | **1.74x** (1.57x) | 110.4 / 62.4 |
| 8 | 50.8 (49.3–54.8) | 69.0 (68.5–69.3) | **1.36x** (1.25x) | 150.1 / 109.5 |

**What was measured:**
- **There was no crossover.** The pool's advantage shrinks as replicas are added, from 2.17x to 1.36x. But it holds even in the worst pairing, the slowest `0` run against the fastest `1` run, which still comes out 1.25x ahead at 8 replicas.
- **The workers were saturated, so in-worker time sets throughput.** Throughput came out at 94–98% of `replicas × 1000 / in-worker ms` in every cell. At this job size, Celery and Redis are no longer the bottleneck that story #9 found.
- **Replicas beat threads.** 8 replicas on one thread each gave 50.8 jobs/s. 1 replica with the full pool gave 20.2, about 2.5x less. Within one process the pool only parallelizes the trial loop, and the DuckDB read, the returns matrix and the Python glue stay serial. On the bare call at 26 assets, the pool sped the loop up about 7.5x. Assuming that holds here, the drop from 105.6 to 48.1 ms leaves roughly 39 ms of each task that no number of threads can shorten. Replicas run that part in parallel as well.
- **Single-threaded tasks slowed down under load too.** In-worker time with `num_threads=1` rose 4.5% at 3 replicas and 42% at 8 (33–47% across passes), with no thread pool involved. The candidate causes were not separated: hyperthread siblings sharing a physical core, DuckDB's own threads, memory bandwidth (each task's weights matrix is about 21 MB), and the gateway, Redis, Prometheus and the benchmark client all running on the same host.
- **A follow-up to story #4:** the pool's speedup on the bare call depends on how much work each trial carries, about 2.4x at 3 assets and about 7.5x at 26. Story #4's 3.3x therefore says more about its small benchmark than about an 8-physical-core ceiling.

**The catch:** the clean result holds only for the deployment it was measured on. Compose sets no CPU limits. `k8s/financial-os.yaml` gives each worker `limits.cpu: "1"`, with the HPA allowing up to 6 replicas. `hardware_concurrency()` reports the node's 16 logical CPUs, not the container's CPU quota. So under that limit, a pod running `num_threads=0` would start 16 threads that share one CPU's worth of time. That allows no speedup, and CFS throttling would probably make it slower. This was not measured on Kubernetes. The defaults in force at the time would have hidden the problem in opposite directions. With the request default left at `1`, Compose gives up a 1.36–2.17x speedup. Change it to `0`, the default these numbers argue for, and every k8s pod runs a 16-thread pool on one CPU.

**Decision:** the deployment sets the default and the request can override it. `num_threads` in `OptimizeRequest` is now optional. When a request leaves it out, the worker fills it in from `FOS_OPTIMIZE_THREADS`: `0` in `docker-compose.yml`, and `1` on the k8s worker container, set next to the CPU limit it depends on. An unset variable means `1`, which is safe under any limit. Since the caller no longer necessarily picks the value, the job result now reports the `num_threads` that actually ran. A value other than `0` or `1` fails the optimize job with a readable error, at call time rather than import time. Story #8 showed that an import-time failure means a crash-looping worker and a queue that stays `PENDING` forever.

**What the reported value caught on the first run:** the first Compose check of a request without `num_threads` came back with `"num_threads": 1`. `docker-compose.yml` had been typed as `FOS_OPTIMIZE_THERADS`. Compose passes any variable name through without complaint, so the worker looked up the correct name, found nothing, and fell back to its safe default. The job succeeded with sensible weights, so the result field was the only sign that the setting never arrived. With the name fixed, the same request returned `"num_threads": 0`. This is story #12's failure class at the configuration layer: a misspelled setting can't be told apart from a correct one left at its default. That is the reason the job result reports the value that actually ran.

**Left open:** the engine-level fix would be to size the pool from the container's CPU quota (`/sys/fs/cgroup/cpu.max`) instead of `hardware_concurrency()` (done later; see story #16). That would make the pool correct under any limit, and would let `num_threads` go back to being an actual count. It was not done because it changes the C++ core for a deployment shape this project only runs locally. The +42% slowdown at 8 replicas is also unexplained. A run that pins one replica per physical core would tell whether hyperthread siblings are the cause.

**Why it matters:** this is the same compounding as stories #7 and #11, one layer down. Phase 4's pool sizes itself from `hardware_concurrency()`, a number that was true on the bare host and became wrong once a container runtime put a CPU quota between the process and the cores. The Compose numbers were the most repeatable of any measurement in this project, three passes with the winner never in doubt. That consistency made them easy to promote to a global default, but it says nothing about a deployment that limits CPU differently.

---

## 14. A writer arrives: the ingestion service writes a copy and swaps it in (post-roadmap expansion)

**Context:** Until this point nothing in the distributed stack wrote to `market.duckdb`. Workers mounted it read-only, and data arrived only when someone ran a local script (`universe_demo.py` and three others) that opened the live file read-write and ingested into it. A write-side ingestion service raised the question of how one writer and the workers' readers can share an embedded single-file database.

**What was measured before designing** (DuckDB 1.5.4, Docker Desktop on WSL2):
- A read-write open fails while any other process has the file open, read-only included, and every read-only open fails while a writer has it. Only readers can share. The lock holds across the container boundary: a write lock held on the host blocked a container's read-only open (`Conflicting lock is held in PID 0`).
- A single-file bind mount stays pinned to the file that was there when the container started. After a 3-row file was renamed over a 1-row file on the host, a file mount still showed 1 row and a directory mount showed 3.
- A reader that has the old file open keeps reading it after the rename, and any other process sees the new file. Within one process, DuckDB keeps reusing an already-open database, so a reopen sees the new file only after every connection to the old one is closed.
- The file is 2.5 MB, so copying it on every write is cheap.

**Options:** (A) write into the live file and let the workers' retries absorb the conflicts; (B) write a copy and swap it in with `os.replace`; (C) replace DuckDB with a database server such as Postgres. C handles concurrent readers and writers properly and removes story #11's single-node limit, and it is planned. B was built first as a stepping stone. Its task, queue, service and endpoint carry over to C; only the storage internals in `data_store.py` and the directory mounts will be replaced.

**The design (B):** the database moves to `data/`, and containers mount the directory. `data_store.ingest_snapshot` downloads first, with no lock held. It then copies the file within `data/`, inserts into the copy, checkpoints it, and `os.replace`s it over the live file. The copy-write-replace sequence runs under an `fcntl` lock on `data/.ingest.lock`, which was also checked across the container boundary. Without that lock, two writers could each copy the same version, and the second rename would silently drop the first one's rows. `POST /ingest` sends `ingest_symbols` to an `ingest` queue. Its only consumer is a one-replica `ingester` with a read-write mount, running as the host uid so the files it creates stay writable locally. The compute workers keep read-only mounts and the default queue. The four local scripts that wrote in place now call the same function and open their read-only connection after it.

**Measured under load** (`benchmarks/ingest_under_load.py`): 3 workers and 2000 three-symbol MACD backtests per run, with writes running the whole time. Each task holds a read-only connection for its entire run.

| Writes during the run | Jobs failed | Task retries | Throughput |
|---|---|---|---|
| None (baseline) | 0 / 2000 | 0 | 84 jobs/s |
| Copy and swap: `POST /ingest` back to back, 15 swaps of 0.3–1.2 s each, download included | 0 / 2000 | 0 | 82 jobs/s |
| In place: write lock held 0.5 s, every 1.5 s | 172 / 2000 | 2065 | 65 jobs/s |
| In place: write lock held 5 s, every 6 s | 1571 / 2000 | 5343 | 78 jobs/s* |

\*Failed jobs end quickly, so throughput flatters this row. The failure count is the meaningful number.

Every failure was `IO Error: Could not set lock on file "/app/data/market.duckdb"`. Each failed job had already been retried three times with backoff by the `autoretry_for=(duckdb.IOException,)` the tasks already had. The 5 s hold does not exaggerate the old scripts. `ingest_many` held its read-write connection while it downloaded each symbol in turn, so `universe_demo.py`'s 26 symbols kept the file locked for several seconds per run. Every swap really did produce a new file: one ingest that inserted no rows still changed the inode from 74505 to 321739.

**A prediction that did not hold:** the argument against writing in place said the writer would rarely find a gap, because workers near saturation keep the file open almost all the time. It did find gaps. Every in-place writer got its lock within 0.22 s, after at most 25 attempts 5 ms apart: each backtest task closes its connection when it finishes, and gaps across the three workers line up often. All of the damage fell on the readers instead.

**Two things found along the way:**
- **Dependency drift.** Unpinned installs gave CI and the rebuilt worker image DuckDB 2.0.0 while the venv ran 1.5.4. Version 2.0 refuses a new statement while an earlier result is still unfinished, and `fetchone()` leaves it unfinished, so `ingest_snapshot` failed in CI. A file *created* by 2.0 has storage version 999, which 1.5.4 cannot open; a 1.5.4 file that 2.0 modifies stays readable. `constraints.txt` now pins the venv's versions for both images and CI.
- **Retries are counted as failures.** The worker's metrics label every non-SUCCESS task run `failure`, retries included, so `celery_tasks_total{status="failure"}` overstates real failures. This measurement counts retries as attempts minus jobs instead. Fixed right after: a retry now gets its own `retry` label, and `services/tests/test_metrics.py` checks all three states.

**Known limits:** a walk-forward job whose tasks run across a swap can read two versions of the data. Existing rows never change, so only windows that reach past the old last date can differ. The k8s `ingester` has not been run on a cluster, and if `/host-mount` comes from `minikube mount` over 9p, file locks there may not behave as they do on a bind mount. Like DuckDB itself, B is single-node by construction.

**Why it matters:** the obvious design, writing into the file the readers use and letting retries absorb the conflicts, fails badly here. A 5 s write lock failed 79% of the jobs running alongside it, and even half-second writes failed 9%. Measuring the locking rules first pointed to copy-and-swap, and measuring it under load showed it costs the readers nothing. It also repeats the lesson of stories #7 and #11: the constraint came from an earlier storage decision, an embedded single-file database, and only surfaced once the system gained a writer.

---

## 15. Postgres replaces DuckDB: the copy-and-swap was a bridge (post-roadmap expansion)

**Context:** Story #14 kept DuckDB and worked around its file lock: the ingester writes a copy and swaps it in. That design was chosen knowing it would be replaced, as a step toward a database server that lets readers and writers work at the same time. This story covers the switch and what it measured.

**What changed:** `data_store.py` now uses psycopg 3 against Postgres 18: a Compose service with a named volume, and a StatefulSet on Kubernetes. An ingest downloads first. Then, in **one transaction**, it `COPY`s the rows into a temporary staging table that empties itself on commit and runs one `INSERT ... ON CONFLICT DO NOTHING`, whose row count is exactly the rows that were new. Readers see the whole ingest or none of it, and never wait for it. A second writer inserting the same rows waits on the primary key and then skips them, so concurrent ingests are safe.

What carried over from story #14: the `ingest_symbols` task, the `ingest` queue and its `ingester` service, `POST /ingest` with its tests, and one write function for every local script. What was thrown away: the copy-and-swap internals, the lock file, the `data/` directory mounts, and the ingester's fixed uid and `Recreate` strategy. Tasks now retry on `psycopg.OperationalError` (the database briefly unreachable) instead of on lock errors, which no longer exist. The data-store tests run against a real Postgres: the Compose service locally, a service container in CI, in their own `fos_test` database. They error rather than skip when it is missing.

**The migration was verified, not assumed:** `migrate_duckdb_to_postgres.py` copied all 34,166 rows and compared both sides row by row, with exact float equality: identical. The reference 3-symbol MACD backtest returned the same `1255` bars, `34` trades and `98337.99530891428` final equity, on Compose and on the Kubernetes cluster. The comparison's first version built a set inside a list comprehension, so it rebuilt the set for each of the 34,166 rows and took 2 minutes. Built once, it took 1.2 s. That is the same quadratic-loop mistake as story #2, in a one-off script.

**Measured under load** (the same benchmark and setup as story #14: 3 workers, 2000 three-symbol MACD backtests per run):

| Writes during the run | Jobs failed | Task retries | Throughput |
|---|---|---|---|
| None (baseline) | 0 / 2000 | 0 | 113 jobs/s |
| 11 committed ingests (`POST /ingest`) | 0 / 2000 | 0 | 112 jobs/s |
| A write transaction held open 5 s: 1,255 inserts plus an update of all 1,349 SPY rows the backtests read, then rolled back | 0 / 2000 | 0 | 112 jobs/s |
| An `ACCESS EXCLUSIVE` table lock held 5 s | 0 / 2000 | 0 | 21 jobs/s |

The third row is the direct counterpart of story #14's worst case. A 5 s DuckDB write lock failed 1,571 of 2,000 jobs. A 5 s Postgres write transaction that held row locks on every SPY row the readers needed failed none and cost nothing: readers were served the last committed version of those rows. The fourth row shows what still blocks. A table-level lock, the kind `TRUNCATE`, `ALTER TABLE` and `LOCK TABLE` take, makes readers *wait*, so every job still succeeded but throughput fell to a fifth. Ordinary writes never take that lock, but schema changes do, so they need an idle stack. The baseline was 113 jobs/s here against 84 under DuckDB in story #14. Opening a DuckDB file on every task plausibly cost more than a Postgres connection, but the two figures come from different sessions, so this is an observation, not a controlled comparison.

**Kubernetes, verified on a cluster this time:** on a 2-node minikube, workers ran on both nodes, and the ingester ran on the node that did not hold the database. All of them reached it over the network: 300 backtests split 101 / 101 / 100 across the three workers, and the reference result came out identical. This lifts story #11's limit, which required every worker on the one node holding the DuckDB file.

**What the cluster test found:** the limit did not vanish; it moved to the database's storage. minikube's default storage class provisions a `hostPath` volume with no node affinity, so nothing keeps `postgres-0` on the node that holds its data. Three restarts happened to land on the same node and kept all 35,420 rows. With that node cordoned, `postgres-0` started on the other node and initialized a new, empty database there: 47 MB, next to the real 66 MB left behind on the first node. Nothing was lost, but until the pod moved back, every query would have run against an empty table. The manifest now states the requirement: the claim needs a storage class whose volumes carry node affinity, as cloud disk drivers and local-path provisioners provide.

**Fixed right after:** the claim now names `storageClassName: local-path`, from minikube's `storage-provisioner-rancher` add-on, whose volumes are bound to the node that first runs the pod. The class is named explicitly so that a cluster without a suitable class leaves the claim `Pending`, a loud failure, instead of quietly falling back to the default. The same forced move was repeated on a fresh 2-node cluster. The volume carried node affinity for `minikube-m02`, and with that node cordoned `postgres-0` stayed `Pending` (`1 node(s) didn't match PersistentVolume's node affinity`) rather than starting anywhere else. A backtest sent during the outage failed after 19 s of Celery retries (`failed to resolve host 'postgres'`, since the Service had no ready pod), so it failed loudly instead of reading an empty table. Uncordoned, the pod came back on its node with all 35,420 rows, and the reference result was unchanged. What remains is the usual trade-off of a single database replica: while its node is down, the system is down. Surviving that would take a replicated database, not a different volume.

**An environment detail that cost a round trip:** a native PostgreSQL 18 on the WSL host already listened on `127.0.0.1:5432`. The first migration therefore reached that server, not the container, and failed with `password authentication failed for user "fos"`. The scratch tests had used port 55432, so they never touched 5432 and could not catch it. Compose now publishes the container on host port 5433.

**Why it matters:** story #14 measured why DuckDB could not take a writer and built a way around it. This story removed the reason for the workaround, and the same benchmark that recorded 79% failures under a 5 s DuckDB write lock recorded zero under a 5 s Postgres write transaction. Both changes ended the same way, though: the constraint moved rather than disappeared. In story #14 it moved from the file to how the file is mounted, and here from where the workers can run to where the database's storage lives. It took a second node to see it, because on a single node every restart comes back to the same disk.

---

## 16. The thread pool learns how many CPUs it may use (post-roadmap expansion)

**Context:** story #13 left the Optimizer's Monte Carlo pool sized by `std::thread::hardware_concurrency()`, which reports the machine's CPUs (16 here), not what a container may use. The workaround was a per-deployment default: `FOS_OPTIMIZE_THREADS` was `0` (all cores) on Compose, which has no CPU limit, and `1` on k8s, whose workers are capped at 1 CPU. The story predicted that a 16-thread pool under a 1-CPU quota would be throttled and probably slower, but never measured it.

**Measured first:** the 26-asset, 100k-trial search was timed inside the existing worker image under `docker run --cpus`, 20 calls per setting, reading the cgroup's `cpu.stat` throttling counters around the timed calls:

| CPU limit | `num_threads=0` (16-thread pool) | `num_threads=1` | Throttled periods with the pool |
|---|---|---|---|
| none | 12.9 ms median, 16.9 ms p90 | 79.0 ms | 0 |
| `--cpus 2` | 49.1 ms, **95.4 ms p90** | 78.7 ms | every one (10/10) |
| `--cpus 1` | **105.5 ms, 197.2 ms p90** | 84.7 ms | every one (28/28) |

Under a 1-CPU quota, "use all cores" was 25% slower than one thread at the median and 2.1x worse at the p90: story #13's suspicion, now measured.

**The change:** `Optimizer::usable_cpus()` starts from `hardware_concurrency()`, caps it by the affinity mask (`sched_getaffinity`, which `--cpuset-cpus` sets), and caps that by the CFS quota (`/sys/fs/cgroup/cpu.max`, with the cgroup v1 files as a fallback), rounding the quota up. One static pool of that size serves every call, and `num_threads` became a real count: `0` uses the whole pool, `N` splits the trials into at most `N` blocks, and `1` runs inline without the pool. It is exposed to Python as `Optimizer.usable_cpus()` and reported in every optimize result. The gateway now accepts `0` to `256` instead of only `0` or `1`. The worker's default became `0` everywhere, so the per-deployment `FOS_OPTIMIZE_THREADS` lines in `docker-compose.yml` and the k8s manifest were deleted rather than adjusted. Two new GoogleTest cases check that `usable_cpus()` stays within the machine and that every thread count, including more threads than any machine has, returns a fully invested portfolio. Both compilers pass all 18.

**Prediction, recorded before the change was built:** about 80–85 ms with no throttling at 1 CPU, about 40–45 ms with the p90 close to the median at 2 CPUs, and no change without a limit. **Measured after**, in a worker image built from the change:

| CPU limit | Pool size | `num_threads=0` median | p90 | Throttled periods |
|---|---|---|---|---|
| none | 16 | 11.6 ms | 13.0 ms | 0 |
| `--cpus 2` | 2 | 47.6 ms | 54.5 ms | 0 of 9 |
| `--cpus 1` | 1 | 81.4 ms | 88.4 ms | 0 of 16 |
| `--cpus 1.5` | 2 (rounded up) | 64.2 ms | 69.6 ms | 12 of 12, but 0.5 s throttled in total |
| `--cpuset-cpus 0,1`, no quota | 2 | 47.0 ms | 51.9 ms | 0 |

The 1-CPU prediction held (81.4 ms, no throttling), and so did the unlimited one. **The 2-CPU prediction was half wrong.** The median barely moved, 49.1 ms to 47.6 ms, not the predicted 40–45 ms. The whole gain was in the tail: the p90 fell 43%, and throttling stopped. Sixteen threads under a 2-CPU quota did the same total work. What they added was stalls: whole periods in which every thread waited for the quota to refill, and a call finished only when its slowest block did. **Rounding up held:** at 1.5 CPUs, two threads finished in 64.2 ms, while one thread takes about 81 ms. The cost was some throttling, 0.5 s in total against the 16-thread pool's 7.3 s at 2 CPUs.

**Why it matters:** story #13 fixed the symptom where it showed up, in the deployment config: each deployment had to know its own CPU limit and set a matching default. That is the kind of setting that goes stale the first time someone changes `limits.cpu`. Here the engine asks the kernel instead, so every deployment now runs with the same default. The measurement also corrected the expectation of what oversubscription costs. At a whole-CPU quota the cost lands mostly in the slowest calls, not the typical one, so a median-only benchmark would have called the change pointless at 2 CPUs.
