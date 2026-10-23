# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Working rules

- **Do not edit non-Markdown files directly — show the user the code instead.** Source (`.rs`, `.cpp`, `.hpp`, `.py`, `CMakeLists.txt`, `Cargo.toml`) is proposed as code blocks anchored to `file:line`; the user applies every edit. New files go in their own section. `.md` files are the exception: edit those in place and say what changed.
- **All executions are done by the user.** Do not run `cargo`, `cmake`, the engine, or the benchmarks yourself — give the command and wait for the pasted output. A latency number Claude produced is a number the user cannot defend in an interview, which is the entire point of this project.
- **Everything is in English** — code comments, docstrings, commit messages, and chat explanations to the user.
- The git root is **`/home/anstk/Projects`**, not this directory. `portfolio/` is currently untracked, and the existing `.github/workflows/smoke.yml` is scoped to `graduate/**`, so nothing here runs in CI yet.

## What this is

Portfolio project 1 of 3 (`portfolio/project_2` = Monte-Carlo pricing / risk, `portfolio/project_3` = Rust→ML feature pipeline). They are independent deliverables, not one system.

**`Project_1_C++Rust_Hybrid_Ultra-Low.txt` is the spec and the only source of truth in this directory — but its code blocks are illustrative, not normative.** The prose requirements bind; the struct definitions, the polling loop and the Python snippet are sketches of intent, so do not treat their field offsets, names, signatures or omissions as decisions already made. Code so far covers the IPC layer only: the ring (`ring.hpp`), the event schema (`market_event.hpp` / `router/src/event.rs`), symbol codegen (`tools/gen_instruments.py` from `instruments.csv`), and three CMake benchmark/diagnostic targets (`noise_floor`, `ring_bench`, `layout_dump`). There is no order book, fill model, or Python package yet. Build/check commands, for the user to run: `cmake -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j`, `cargo test --manifest-path router/Cargo.toml`, and `./tools/gen_instruments.py --check` (exits 1 if a generated file has drifted from the CSV). Toolchain present on this machine: cargo 1.93, cmake 4.2, g++ 15.2 (C++20 fine), python3 3.14, valgrind 3.26, 16 cores, x86_64, `/dev/shm` mounted at 3.9G.

Goal: a tick-level (L2/L3) event-driven backtester that reconstructs market microstructure — slippage and queue position — at microsecond resolution, split across three processes.

## Architecture: three processes, one shared-memory contract

```
Rust Data Router  ──write──▶  POSIX shm ring buffer  ──poll──▶  C++ Core Engine  ──pybind11──▶  Python
(tokio, WebSocket)            (SPSC, 64B slots)                 (LOB, fills, PnL)             (research)
```

- **Data Router (Rust)** — `tokio` + `tokio-tungstenite` holds the exchange WebSocket connections, parses JSON ticks, converts them to fixed-length binary events, and pushes into an `mmap`ed SPSC ring buffer. Sole producer.
- **Core Engine (C++20)** — spins on the ring buffer's tail, updates the limit order book, simulates fills, computes PnL. Sole consumer, pinned to one core.
- **Research Interface (Python 3.10+)** — a pybind11 module driving the engine — construct an environment over a named shared-memory segment with a configurable latency model, run, then read PnL and latency series back. Results return to NumPy **zero-copy**, so the C++ buffer must outlive the NumPy view. Module and class names in the spec are placeholders.

### The IPC schema is the load-bearing invariant

The event struct is declared **twice** — once in Rust, once in C++ — with no generated binding tying them together. The two declarations are the whole contract, and a silent mismatch corrupts every downstream number rather than erroring. Design requirements the spec actually states:

- **One event is fixed-length and pinned to a 64-byte cache line**, to keep fragmentation and cache misses out of the hot path. Layout is still open — the spec's field list is a sketch — but whatever it becomes, both sides must agree byte for byte, and explicit padding is structural rather than filler.
- **No strings in the hot path.** Symbols are mapped to integer IDs; the mapping needs one shared source of truth generated for both sides.
- **Every event carries both an exchange timestamp and a local receipt timestamp**, so end-to-end latency is measurable from the event itself rather than reconstructed.
- Size and alignment assertions on both sides are the cheapest way to make a mismatch a build failure instead of a silent one.

### C++ hot-path constraints

These are acceptance criteria, not style preferences — one of the deliverables is a Valgrind report proving zero dynamic allocation during simulation.

- **Zero allocation after init.** No `new`/`malloc`/`free` once the main loop starts. Order-book nodes and queues are pre-allocated as memory pools at startup. This bans `std::vector` growth, `std::string`, `std::map`, and any container that allocates on insert from the loop.
- **Spin, don't block.** No `std::mutex`, no `condition_variable` — atomically check the ring tail and issue a pause intrinsic while busy-waiting, so the CPU pipeline is not flushed on every empty poll.
- **Thread affinity.** The engine thread is pinned to a dedicated core to keep context switches out of the measurement.
- **LOB structure:** price levels are a pre-allocated 1D array indexed by price tick — O(1), no hash map. Orders within a level are a doubly linked list whose nodes live in a pre-allocated array and link by **index, not pointer**, for cache locality. Queue position falls out of this list, and queue position is what the simulator exists to model.

## Deliverables (how this project is judged)

1. **IPC latency** — Rust receipt to LOB update, target **< 1μs**.
2. **Throughput** — 10M messages/sec.
3. **Valgrind log** proving 0 dynamic allocations during simulation.

Measurement caveat worth stating up front: this machine is **WSL2**, where the clock is virtualized and cores cannot be isolated (`isolcpus`) from the host scheduler. Sub-microsecond numbers taken here are indicative, not defensible — plan for the headline benchmark to be re-run on bare-metal Linux, and record which environment produced any figure that gets quoted.

## Other documents in this directory

- **`DESIGN.md`** — the ring-buffer protocol: segment layout, index scheme, memory ordering, full-ring policy, lifecycle. The event schema is explicitly out of its scope.
- **`REVIEW.md`** — an imported Gemini architectural review of the current code, with proposed patches. Unverified, and at least one figure in it was wrong when imported: check each claim against the code before acting on it. Its patches are subject to the working rules above like any other edit.
