# Ring Buffer Protocol

The shared-memory contract between the Rust data router (producer) and the C++ core engine (consumer). This is the one interface that spans two languages, two processes and an on-disk format, so it is designed before code; everything behind it — order book internals, fill model, Python API — is deliberately left open.

**Scope.** Segment layout, index scheme, memory ordering, full-ring policy, lifecycle. **Not in scope:** the event schema. The ring treats a slot as 64 opaque bytes; what goes inside is a separate contract with its own document.

---

## 1. Segment layout

One POSIX shared-memory object, `mmap`ed by both processes:

```
┌──────────────────────────────────────────────┐
│ Header — 384 B, three 128 B regions          │
│   ┌────────────────────────────────────────┐ │
│   │   0  static     magic, version,        │ │  ← written at init, then read-only
│   │                 slot_bytes, capacity,  │ │
│   │                 clock_id               │ │
│   ├────────────────────────────────────────┤ │
│   │ 128  producer   write_idx,             │ │  ← producer writes, consumer reads
│   │                 dropped_count,         │ │
│   │                 producer_state         │ │
│   ├────────────────────────────────────────┤ │
│   │ 256  consumer   read_idx               │ │  ← consumer writes, producer reads
│   └────────────────────────────────────────┘ │
├──────────────────────────────────────────────┤
│ 384  Slot array — capacity × 64 B            │
└──────────────────────────────────────────────┘
```

**The regions are grouped by writer, and each is 128 B — not 64.** If `write_idx` and `read_idx` share a line, every producer index update invalidates the line the consumer is spinning on and the two cores ping-pong it on every single event. 128 rather than 64 because Intel's L2 adjacent-line prefetcher works on 128-byte pairs, so 64-byte separation still lets the two indices travel together. The slot array keeps 64-byte elements, where that same prefetcher is a benefit rather than a cost.

Grouping by writer rather than by field is the actual rule, because false sharing is a property of writes. `dropped_count` moves only on a drop and `producer_state` twice per run, and both are producer-written, so putting them in `write_idx`'s region costs the consumer — which reads all three and writes none — nothing, and saves a region. The static block shares no line with anything mutable, so the validation §6 performs on attach never touches a line either side is writing.

Three regions at 128 B is 384 B, and 384 is a multiple of 64, so the slot array starts slot-aligned. This padding is part of the on-disk format, not an implementation detail — that is precisely why it belongs in the frozen contract.

## 2. Index scheme: monotonic counters

`write_idx` and `read_idx` are `u64` counters that **never wrap**. The slot is derived:

```
slot = idx & (capacity - 1)        // capacity is a power of two
```

- empty: `write_idx == read_idx`
- full: `write_idx - read_idx == capacity`
- occupancy: `write_idx - read_idx`, always exact

Wrapped indices force you to either sacrifice a slot or carry a separate full flag, and both make the full/empty test racy under concurrent update. Monotonic counters make it a subtraction with no ambiguity.

Overflow is not a practical concern: at the 10M msg/s target, `u64` exhausts in ~1.8×10¹² seconds, roughly 58,000 years. Do not add wrap handling for it.

**Consequence:** `capacity` must be a power of two, validated at init. The masking is what makes the derivation a single `AND` instead of a division.

## 3. Memory ordering

Standard release/acquire handoff. The index store publishes the slot payload.

**Producer (Rust):**
```
1. if write_idx - cached_read_idx == capacity:
       cached_read_idx = load(read_idx, Acquire)      // only when it looks full
       if still full → apply full-ring policy (§5)
2. write slot[write_idx & mask]                        // plain stores
3. store(write_idx, write_idx + 1, Release)            // publishes step 2
```

**Consumer (C++):**
```
1. if read_idx == cached_write_idx:
       cached_write_idx = load(write_idx, Acquire)     // only when it looks empty
       if still empty → pause and retry
2. read slot[read_idx & mask]                          // plain loads
3. store(read_idx, read_idx + 1, Release)              // frees the slot
```

The `Release` on `write_idx` and the matching `Acquire` are what make the slot writes visible; the payload itself needs no atomics. **On x86-64 these compile to plain `MOV`** — the ordering is free at runtime and exists for the compiler — but they must still be written, and they become real barriers if this is ever run on ARM.

**The consumer's `pause` in step 1 is measured, not conventional.** All three strategies available on this host were run against each other: a tight spin with no PAUSE is *slower*, because exiting a hammered spin loop costs a memory-order machine clear larger than the PAUSE granularity it saves, and `UMWAIT` — which the hardware does support here — is slower still at p50 and roughly five times worse at p99.9. PAUSE wins. See §11.

**No per-slot sequence numbers.** They are required for MPMC rings (Vyukov) and are commonly copied into SPSC designs where they buy nothing. With one producer and one consumer, the index handoff alone excludes tearing.

## 4. Cached indices

Each side keeps a **private, non-shared** copy of the other's index and consults the shared line only when the cached value says it must stop. Without this, every push reads a line the other core owns, which is the dominant cost in a naive ring — it turns a local check into a cross-core transfer on every event.

The cached copies live in process-local memory, never in the segment.

**Consumer batching:** having taken one `Acquire` load of `write_idx`, drain every event up to it before reloading. This amortizes the only cross-core read across the whole batch and is the main lever for the throughput target, as distinct from the latency target.

## 5. Full-ring policy

Two different correct answers, and the choice must be explicit per source:

| Source | Policy | Why |
|---|---|---|
| Synthetic replay (benchmarks) | **Spin / backpressure** | The measurement is sustained throughput. Dropping events would let the ring report a rate it did not actually deliver. |
| Live exchange feed | **Drop + count** | Backpressure cannot be applied to an exchange. Stalling the tokio task only moves the overflow into the kernel socket buffer, where it is invisible. |

**In both cases `dropped_count` is incremented and lives in the header** so that the engine and the Python report can read it.

**A run with `dropped_count > 0` is reported as invalid, not silently used.** Silent loss is the failure mode that destroys a backtest's credibility, and it is undetectable after the fact unless the counter is carried alongside the results.

## 6. Lifecycle

**The C++ engine creates and sizes the segment; the Rust router attaches and retries until it appears.** The engine is the consumer and the process that defines a run — if the router created it, a stale segment left by a crashed router could be attached with a different capacity, which is unrecoverable and silent.

On attach, the router validates `magic`, `version`, `capacity` and `slot_size`. **A mismatch is a hard failure, never a warning** — this is the only guard against a stale segment or a version-skewed binary, and it is the failure this whole document exists to make loud.

The engine `shm_unlink`s on shutdown. Stale objects in `/dev/shm` outlive the process and will be attached by the next run.

`producer_state` in the header lets the engine distinguish "router not started yet" from "router exited" without a timeout heuristic.

## 7. Sizing

64 B per slot, power-of-two capacity. The L3 column is the one that decides, and §12 is why:

| Slots | Segment | vs 18 MiB L3 | Burst absorbed at 10M msg/s |
|---|---|---|---|
| 65,536 | 4 MiB | resident | 6.6 ms |
| 131,072 | 8 MiB | resident | 13.1 ms |
| 262,144 | 16 MiB | at the edge | 26.2 ms |
| 1,048,576 | 64 MiB | 3.6× over | 105 ms |

**The 1 Mi default was wrong and §12 retired it.** The argument for it was sound as far as it went — the consumer's stall has no converged maximum on this host, a 30 s pinned spin peaking at 1.07 ms and a 5 s run at 4.12 ms, so the observed max is a draw from a heavy tail rather than an estimate of it. What the argument never priced was the cache. A 64 MiB ring exceeds L3 by 3.6×, so every wrap-around store misses to DRAM, and it measured 61.29 M msg/s against 294.79 for a 4 MiB ring — a 4.8× throughput penalty paid for absorption the run never used, since `full-stalls` was 0.

**The rule is the largest power of two that stays in L3, sharing it with the consumer.** Absorption and throughput are in direct opposition and the L3 boundary is where the trade is made; `/dev/shm` at 3.9 G never binds.

**128 Ki is the default, and at n=3 the sweep decides it rather than merely permitting it.** §12 measured 4 MiB and 8 MiB as indistinguishable on throughput — 261-332 against 257-372 M msg/s, ranges that overlap almost completely — so throughput does not choose between them. Dwell time does: the producer is blocked on a full ring for 0.06-0.55% of the run at 4 MiB and 0.000-0.033% at 8 MiB, an order of magnitude apart and in the direction a larger ring predicts. 8 MiB also gives 13.1 ms of absorption at the target rate against 4 MiB's 6.55 ms, where the worst stall §11 recorded was 4.12 ms on a distribution that had not converged. Above that, 16 MiB costs half the throughput while still fitting inside 18 MiB of L3, so it is excluded on measurement rather than on the cache arithmetic.

**The constraint to carry to another host is half of L3, not L3.** The measured cliff is between 8 and 16 MiB against an 18 MiB cache, because L3 is shared and 12-way associative and a ring at 89% of it conflict-misses on the wrap-around store. 8 MiB is already 44% of this machine's L3, which is at that edge — and **every number behind this choice was produced by a consumer that only walks a sequence counter.** Once it carries the book and competes for the same cache, the capacity has to be measured again; 64 Ki is the fallback if it does.

**Huge pages for the slot array are worth an `mmap` flag and were never a blocker.** The TLB cost is smaller than it looks: the ring is swept cyclically at 64 slots per 4 KiB page, so it is one page walk per 64 events — under 2 ns per event amortized. 2 MiB pages make it one walk per 32,768. Take it if it is free; it does not decide the capacity, and after §12 nothing about the TLB does.

## 8. Constraints the ring imposes on the slot payload

The event schema is a separate contract, but the ring fixes four properties of it:

1. **Fixed length, 64 B, 64-byte aligned** — one slot is one cache line, and the index arithmetic in §2 assumes a constant stride.
2. **Trivially copyable / POD** — no constructors, no destructors, no vtables. A slot is published by a plain store, not by running code.
3. **No pointers or references.** The segment can be mapped at a different base address in each process; an address written by the router is meaningless to the engine. Use offsets or integer IDs.
4. **Both declarations must agree byte for byte** — see §10.

The schema that satisfies these is `MarketEvent`, specified in §13.

## 9. Latency measurement hook

End-to-end latency is measured across a process boundary, so it constrains the protocol rather than sitting on top of it:

- The producer stamps its receipt time into the slot **immediately before** the `Release` store, so the interval excludes its own parse work.
- The consumer reads its clock immediately after the `Acquire` load succeeds.
- **Both processes must read the same clock source**, recorded in the header's `clock_id`. Changing it invalidates every number measured before the change, which is why it is pinned in the contract rather than chosen per call site.
- **`clock_id` is `RDTSCP`.** It costs 11–12 ns against 15–16 ns for `clock_gettime`, and on a quantity whose floor is ~41 ns that difference is not rounding. The condition this was held on — invariant TSC fixes a common *rate*, not a common *origin*, so a per-vCPU offset would be added to every cross-core figure and could make it negative — is discharged in §11: the offset is bounded inside ±40 ns on all 15 pairs and every interval contains zero.
- **Calibrate the TSC frequency once per run and never hardcode it.** Two runs an hour apart returned 2.8363 and 2.8276 GHz, 0.31% apart, while the two calibrations *inside* each run agreed to 0.0003%. The counter is stable; the short calibration against `CLOCK_MONOTONIC` is what moves. 0.31% is 0.2 ns on a 70 ns interval and irrelevant now, but it is not irrelevant to anything cumulative.
- **Report the clock's own cost beside the latency.** Two `RDTSCP` reads are ~23 ns on a handoff whose floor is ~41 ns one-way, more than half the figure. A latency number quoted without it is largely quoting the instrument.
- Report **p50 / p99 / p99.9, never a mean.** Collect into a histogram from the first commit; a mean latency cannot be reconstructed into a tail afterwards.

## 10. Keeping the two declarations in sync

There is no generated binding — the Rust and C++ declarations are written by hand and nothing ties them together. Two guards, both cheap:

1. **Size and alignment assertions on each side**, evaluated at compile time, so drift is a build failure.
2. **A layout check in CI:** a small binary in each language emits every field offset plus the header offsets, and the two outputs are compared. Assertions catch a size change; only an offset dump catches two structs that are both 64 bytes with fields in different places.

## 11. Measured noise floor (2026-08-29, WSL2)

Measured by `noise_floor.cpp` before any of this protocol was written, over three runs. These are the numbers every later latency figure is reported against; re-run it on any new host before quoting anything from that host.

Host: i5-12500H (physically 4 P-core + 8 E-core) under Hyper-V/WSL2, 16 vCPUs, TSC 2.83–2.86 GHz.

| Quantity | p50 | p99 | p99.9 | max |
|---|---|---|---|---|
| `clock_gettime(CLOCK_MONOTONIC)` | 16 ns | 18 ns | 33–36 ns | 74 µs |
| `clock_gettime(CLOCK_MONOTONIC_RAW)` | 15 ns | 16 ns | 17 ns | 625 µs |
| `RDTSCP` | 11–12 ns | 12–13 ns | 13–15 ns | 556 µs |
| `_mm_pause()` | 58 ns | 58 ns | 142–261 ns | — |
| Core-to-core RTT, PAUSE spin | 135–163 ns | 223–248 ns | 242–262 ns | — |
| Core-to-core RTT, tight spin | 172–207 ns | 211–246 ns | 240–352 ns | — |
| Core-to-core RTT, `UMWAIT` C0.1 | 169–188 ns | 230–267 ns | 720–1751 ns | — |
| Pinned spin-loop gap | 18 ns | 20–21 ns | 37–38 ns | 0.60 / 1.07 / 4.12 ms |

Bands are across the 15 vCPU pairs and across runs. Per-pair medians move 5–10% between runs, so a difference smaller than that is only meaningful when both arms were measured in the same run — which is how the three spin strategies were compared. Two per-pair artefacts in the third run illustrate the point and should not be read as structure: one pair returned p50 221 ns with a normal p99, and one returned p99.9 6786 ns. At n=200k the p99.9 rests on ~200 samples and a single preemption during that pair's 30 ms moves it.

**TSC is usable as a timebase, and the cross-core origin is common.** Calibrations inside a run agree to 0.0003%, and zero-delta was 0.00% on both `clock_gettime` variants, so the 1 ns resolution is real rather than a coarse counter being interpolated. All three reads stay in userspace; a syscall would be an order of magnitude dearer. The responder's own stamp bounds the per-vCPU TSC offset to within ±40 ns on all 15 pairs in both runs that measured it, every interval containing zero. That bounds the offset rather than measuring it, and nothing below ~40 ns is resolvable this way, but the µs-to-ms desync that would have made cross-core stamping useless is excluded.

**The vCPU numbering carries no locality information.** All 15 pairs land within a narrow band of each other in every spin mode. On real hardware a hyperthread pair sharing L1 is several times faster than a cross-core pair, and Alder Lake's P-to-E handoff differs again; here `cpu 0 <-> 1`, which the kernel reports as siblings, is no faster than `cpu 0 <-> 15`. The topology is fabricated and pinning to a vCPU is not pinning to a physical core. The consequence is benign: the core-pair choice, normally the dominant variable in a benchmark like this, can be neither tuned nor got wrong.

**PAUSE costs 58 ns and is still the fastest of the three spins.** This was measured expecting the opposite. Differencing the modes within a run gives a consistent model. PAUSE adds an average half-PAUSE per direction, so `148 = 2C + 58` puts the coherence round trip at ~89 ns and the **one-way handoff floor at ~45 ns**; the same arithmetic on the earlier run gave 41 ns, so that floor is reproducible. From there `201 = 89 + 2M` puts the cost of exiting a hammered spin loop at ~56 ns per exit, and `184 = 89 + 2W` puts the `UMWAIT` C0.1 wakeup at ~48 ns per wait — more than the 29 ns half-PAUSE it replaces, which is why it loses. The standard explanation for the spin-exit term is a memory-order machine clear, speculative loads on a line that then gets invalidated, which is what PAUSE exists to avoid; the attribution is arithmetic here, not measured, since the PMU is not exposed under WSL2. Independent corroboration: the TSC-offset interval width is a lower bound on the minimum round trip, and it runs ~70 ns with PAUSE against ~110 ns without.

**`UMWAIT` is rejected, and its tail is the reason.** WAITPKG is exposed to the guest and the instruction executes, so this is a real result rather than a missing feature. It loses p50 to PAUSE by ~36 ns, which the wakeup arithmetic above explains, and it loses p99.9 by a factor of four to five — 720–1751 ns against 242–262 ns. The plausible mechanism is that parking a logical core into C0.1 is exactly the signal a hypervisor reads as "this vCPU is idle", and the resume then waits on the host scheduler; that mechanism is inference, but the tail is measured and it is disqualifying on its own. **A latency-critical wait inside a VM must not tell the host it is idle.**

**~45 ns one-way is the handoff floor, so the instrument is now a large share of the measurement.** Two `RDTSCP` reads are ~23 ns against a 45 ns floor. Every reported end-to-end latency must carry the clock cost beside it, or half of what is being quoted is the clock.

**The sub-microsecond target is a p99.9 claim, and the ring size is set by a tail that has not converged.** A 45 ns floor leaves ~95% of a 1 µs budget and the per-pair p99 of ~230 ns is comfortable. The scheduler is the whole problem. Above 10 µs the rate is stationary across runs — 264, 257 and 232 per second — but the far tail is not: three runs produced maxima of 0.60, 1.07 and 4.12 ms, a sevenfold spread, and the run that found the worst one was the shortest. A shorter run finding a worse max means the observed maximum is a draw from a heavy tail, not an estimate of it. Two consequences, and they are the load-bearing ones in this document: the latency claim survives p99.99 and is false at p99.9995 and at max, and the ring must be sized against a stall nobody has yet seen the top of (§7). No configuration of this code changes either; it is the hypervisor's scheduler. Quote the percentile with the number, always.

## 12. Measured ring (2026-08-30, WSL2, two threads, one process)

`ring_bench` drives `ring.hpp` between two pinned threads with no process boundary and no LOB, so what it isolates is the ring's own cost. Every run finished `RUN VALID` — zero gaps, zero drops, `recv == sent`.

| Mode | Config | Result |
|---|---|---|
| lat | 64 Ki, paced 1M msg/s, batch 1, cpu 0 → 2 | min 56, p50 100, p99 12,157, p99.9 781,950, max 2,248,925 ns |
| lat | same, **reversed** cpu 2 → 0 | min 62, p50 111, p99 18,186, p99.9 340,955, max 977,013 ns |
| lat | same, cpu 0 → 2, **`chrt -f 80`** | min 62, p50 106, p99 571,586, p99.9 664,022, max 703,346 ns |
| tput | 1 Mi slots = 64 MiB, batch cap 1024 | 61.29 M msg/s, 16.3 ns/msg, mean batch 4.9, 0 full-stalls |
| tput | 64 Ki slots = 4 MiB, batch cap 1024 | **294.79 M msg/s**, 3.4 ns/msg, mean batch 76.4, 3 full-stalls |

**One-way handoff is 105.5 ns and the cross-core TSC offset is ±5.5 ns, not the ±40 ns §11 allowed.** The latency here is one-way, so θ enters uncancelled — the round trip §11 measured carries it with each sign and cancels it. Running both directions restores the cancellation in the mean: 100 and 111 give L = 105.5 and θ = 5.5 ns. That assumes the two directions have the same true latency, which §11's finding that all vCPU pairs measure identically supports but does not prove; either way the 11 ns spread bounds the offset *and* any asymmetry at about 5.5 ns each. §9's choice of `RDTSCP` now rests on a bound an order of magnitude tighter than the one it was made on, and the procedure is cheap enough to keep: **always report a one-way latency as the mean of both directions.**

**The additive floor this document used was wrong, and the empirical floor is the min.** §11's ~45 ns coherence and ~23 ns RDTSCP-pair figures were summed into a 68 ns floor. They do not compose that way: the two clock reads bracket the interval rather than sitting inside it, so the instruction's internal delay from issue to TSC snapshot appears with each sign and cancels, exactly as θ does. The evidence is that min is ~59 ns in both directions — below a floor that was supposed to bound it. The consequence is that **no marginal cost for the ring can be obtained by subtracting a constructed number**; what is measured is 105.5 ns end to end, and 59 ns is the best case the same path ever achieved. The 46 ns between them is contention and jitter on an otherwise idle machine, not structure.

**L3 residency is worth 3.3x on throughput, and the cliff is at half of L3 rather than at L3.** 1 Mi slots is a 64 MiB ring against 18 MiB of L3: the producer's wrap-around store lands on a line evicted a full lap earlier, and since it writes 16 of the 64 bytes the partial line forces a read-for-ownership from DRAM. Three runs per point, 1e9 events each so that a run lasts seconds rather than a third of one:

| Slots | Segment | M msg/s (3 runs) | mean | ns/msg | producer blocked on full |
|---|---|---|---|---|---|
| 65,536 | 4 MiB | 332.27 / 277.70 / 260.97 | 290.31 | 3.0-3.8 | 0.551 / 0.099 / 0.064 % |
| 131,072 | 8 MiB | 365.08 / 257.02 / 372.31 | **331.47** | 2.7-3.9 | 0.033 / 0.000 / 0.000 % |
| 262,144 | 16 MiB | 177.62 / 155.65 / 154.62 | 162.63 | 5.6-6.5 | 0.855 / 0.744 / 0.743 % |
| 524,288 | 32 MiB | 104.25 / 87.47 / 105.46 | 99.06 | 9.5-11.4 | 2.887 / 0.000 / 0.115 % |
| 1,048,576 | 64 MiB | 61.29 (n=1) | — | 16.3 | not instrumented |

**4 MiB and 8 MiB are indistinguishable, and 16 MiB reads slower than both at this run length — a qualification the next paragraphs turn out to need.** The first two ranges overlap almost completely (261-332 against 257-372) and no reading of one falls outside the other. 16 MiB reads 155-178 with all three below every reading of the two smaller sizes, and 32 MiB reads 87-105 with all three below every reading of 16 MiB. So the ordering is `{4 MiB, 8 MiB} > 16 MiB > 32 MiB > 64 MiB`, and 331.47 M msg/s is 33x the 10 M target.

**The interesting boundary is that 16 MiB is already on the wrong side of it while fitting inside 18 MiB of L3.** "Fits in L3" is the wrong rule. L3 is shared with every other process on the machine and is 12-way associative over 24,576 sets, so a ring occupying 89% of it conflict-misses on the wrap-around store even though it nominally fits. The measured cliff sits between 8 and 16 MiB — **about half of L3** — which is the rule to carry to any other host rather than the 18 MiB number.

**The n=1 correction in the previous revision of this section was itself an over-correction.** A 4 MiB run had read 294.79 M msg/s and a rerun of the identical command read 153.09, and the higher figure was withdrawn as a favourable draw. At n=3 the range is 261-332, so 294.79 was ordinary and **153.09 was the bad draw** — the low reading was believed because it was the second one, not because it was better evidence. Both came from runs of under a second. The lesson is not that either number was wrong but that n=1 is n=1 in whichever direction it happens to fall, and the withdrawn 4.8x is approximately restored: 331.47 against 99.06 is 3.3x, both at n=3.

**Dwell time turns out to carry the decision that throughput could not.** 4 MiB and 8 MiB tie on throughput, but the producer is blocked 0.06-0.55% of the run at 4 MiB against 0.000-0.033% at 8 MiB — an order of magnitude apart, in the direction a larger ring predicts. That is what chooses 128 Ki in §7, and it is only visible because the counter now accumulates cycles: the episode counts for the same two configurations are 71/41/45 and 98/1/0, which suggest the opposite ordering.

**The diagnostic came back with neither answer, and it invalidated the sweep's error bars.** Doubling `--events` at 16 MiB was supposed to separate a startup transient (blocked time stays near 48 ms) from a proportional cost (it doubles). It did neither: blocked time fell to 19.41 ms, episodes fell from ~24,000-35,000 to 8,945, and throughput *rose* from 155-178 to 249.64 M msg/s — outside the range three runs had established. **A range that three runs agree on is not an error bar if changing the run length steps outside it.** This is the third time in this measurement campaign that the uncertainty rather than the effect was the thing that was wrong.

**What actually predicts throughput is the mean batch, and it does so across every capacity.** Sorting all thirteen throughput runs by mean batch rather than by capacity produces an almost perfectly monotone series — 9.4 → 87.47, 13.8 → 105.46, 14.2 → 104.25, 20.7 → 154.62, 24.9 → 155.65, 30.2 → 177.62, 51.3 → 260.97, 52.1 → 257.02, 64.0 → 277.70, 68.4 → 249.64, 111.7 → 332.27, 154.1 → 365.08, 206.1 → 372.31 — with the capacity labels scrambled through it. 16 MiB appears at 154.62 and again at 249.64 depending only on which batch regime that run settled into. The causal chain is that L3 residency sets the producer's speed, the producer's speed sets how far ahead it drifts between polls, and that drift sets the batch over which the consumer amortizes its one `Acquire`. **Capacity is two steps upstream of the thing being measured**, which is why its effect is real at the extremes and unresolvable in the middle.

**This line of measurement is closed, and not because it converged.** Every L3-resident capacity clears the 10 M target by 15-37×, throughput is not the binding constraint on any deliverable, and this host cannot resolve what remains. 128 Ki stands as the default on the evidence in §7; the honest statement of its support is that 32 MiB and 64 MiB never produced a batch above 14 or a throughput above 106 in any run, that 4 and 8 MiB never produced one below 51 or 257, and that 16 MiB did both. Further precision here has no payoff.

**Real-time priority does not fix the tail, which is the evidence that the tail is the hypervisor.** Under `SCHED_FIFO` 80 the max improved 3.2× (2.25 ms → 703 µs) and p99.9 improved slightly, while p99 went from 12 µs to 572 µs and the share of polls finding a backlog rose from 3.2% to 5.6%. RT throttling is not the explanation: `sched_rt_runtime_us` is 950000/1000000 here, so a throttle would appear as a ~50 ms stall and the observed max is 703 µs. The reading is that RT priority removes the guest scheduler — many short preemptions — and leaves a smaller number of much longer ones that nothing inside the VM has authority over. **A latency claim on this host is therefore capped by the hypervisor and not by this code**, which is what makes the bare-metal re-run a requirement rather than a refinement.

**The p99 comparison between those two runs is not apples to apples, and the metric is at fault.** With a paced producer and batch 1, one long stall inflates every sample in the catch-up burst behind it, so a distribution with fewer but longer stalls reports a worse p99 even when the stall count fell. The max and the backlog share are the honest comparisons; p99 here measures burst length as much as it measures delay. Any tail figure quoted from this harness has to say which of the two it is.

**§4 documents consumer batching and has no producer equivalent, which is a deliberate asymmetry that should be written down.** One Release per batch of published slots would amortize the coherence transfer on `write_idx` the same way one Acquire amortizes it on the read side. It is not being added: it makes an event invisible until its batch closes, which is the wrong trade for a live feed, and 294.79 M msg/s is 29.5× the target. It is recorded because it is the first thing to reach for if throughput ever becomes the binding constraint.

## 13. `MarketEvent`: the payload contract

64 B, one slot, one cache line. Every field is naturally aligned and there is no implicit padding, so the two declarations can be compared offset by offset. The spec's sketch is the starting point; four things changed and each is a decision, not a transcription.

| Offset | Size | Field | Type | Meaning |
|---|---|---|---|---|
| 0 | 4 | `instrument_id` | u32 | index into the generated instrument table; 0 is reserved as invalid |
| 4 | 1 | `event_type` | u8 | 0 Trade, 1 Snapshot, 2 Update |
| 5 | 1 | `side` | u8 | 0 Bid, 1 Ask |
| 6 | 1 | `flags` | u8 | bit 0 SNAPSHOT_BEGIN, 1 SNAPSHOT_END, 2 AGGRESSOR_BUY, 3 GAP_BEFORE |
| 7 | 1 | `reserved0` | u8 | explicit, zeroed |
| 8 | 8 | `exchange_seq` | u64 | the exchange's own update id |
| 16 | 8 | `exchange_ts` | u64 | ns since the Unix epoch, **exchange clock** |
| 24 | 8 | `local_ts` | u64 | **raw TSC** on the router's core, stamped at receipt |
| 32 | 8 | `order_id` | u64 | L3 order identity; 0 when the feed is L2-only |
| 40 | 8 | `price_ticks` | i64 | price in whole ticks of this instrument |
| 48 | 8 | `quantity` | i64 | size in the instrument's smallest quantity unit |
| 56 | 8 | `reserved1` | u64 | explicit, zeroed |

**`price` and `quantity` are integers, and this is the change that matters most.** The sketch had both as `f64`. §5 indexes price levels with a pre-allocated 1D array indexed by price tick, so an `f64` price forces a float-to-integer conversion on the hot path — a divide by the tick size, a rounding decision, and a rounding *convention* that the router and the engine have to agree on without any mechanism forcing them to. Two conventions that differ in the last bit put an order one level away from where it belongs and produce a plausible book rather than an error. Making the router emit whole ticks moves that conversion to the one place that already holds the instrument's tick size and does it once, and it keeps floating point out of the C++ hot path entirely. Quantity has the same argument plus a second one: queue position is maintained by adding and subtracting resting sizes, and float accumulation drifts silently in exactly the number this simulator exists to produce.

**Conversion is decimal-string to integer, never through a float.** The router parses `"43250.50"` at the instrument's `price_decimals` into 4,325,050 units of 1e-2, then divides by `tick_units`. A non-zero remainder means the exchange sent an off-tick price, which is a data error to be reported rather than rounded away.

**`quantity` on an Update is the new absolute resting size at that level, not a delta**, and zero means the level is gone. This is what L2 diff streams send and it is the convention with no accumulated state to get wrong.

**The two timestamps are in different domains and that is deliberate.** `exchange_ts` is wall-clock nanoseconds from a clock this machine does not control, so any exchange-to-local figure derived from it is bounded by the exchange's clock discipline and is a data-quality metric, not a latency measurement. `local_ts` is a raw TSC read on the router's core, which is what makes deliverable §7.1 — router receipt to LOB update — a difference of two TSC values on one host. The header's `clock_id` (§9) names the domain so a segment stamped one way is never read the other. §12 measured the cross-core offset at 5.5 ns; the deliverable runs in one fixed direction, so unlike a latency bench it cannot cancel that offset by averaging and has to subtract it.

**`exchange_seq` and the `GAP_BEFORE` flag exist because a websocket that drops a message does not say so.** The sequence number is the exchange's own, so gap detection is possible at all; the flag is set by the router because the router is where exchange-specific sequencing semantics live, and the engine should not be parsing one exchange's update-id ranges to learn that its book is now wrong.

**`order_id` is what makes the L2/L3 in §1 true rather than aspirational.** Queue position at per-order granularity needs cancels and modifies to find their node in the §5 linked list, and there is no way to do that without identity. It costs 8 of the 24 bytes the sketch left as padding.

**The instrument table is generated for both sides from one CSV**, which is the §1 requirement that symbols never appear in the hot path and that the mapping have a single source of truth. `id` is an index, so the engine's per-instrument arrays are direct-indexed with no hashing.

**Layout is asserted against literal offsets on both sides.** Not against each other — against the same numbers, written twice. Reordering a field on either side fails that side's build, which is the property §10 asks for: a mismatch is a compile error rather than a corrupted run.

---

## Open decisions

- **Benchmark environment.** §12 turned this from a caveat into a blocker and then showed it cannot be worked around from inside: the p99.9 handoff is 781,950 ns against a 1 µs deliverable, and `SCHED_FIFO` 80 improved the max 3.2× while leaving a ~600 µs tail that RT priority has no authority over. The headline number does not exist on this host at any percentile above the median. WSL2 cannot isolate cores or expose real topology, and §11 prices that precisely: the floor is fine — ~45 ns one-way, a common TSC origin, 1 ns clock resolution — and the tail is not, at ~250 preemptions per second above 10 µs and a millisecond-scale maximum that does not converge over three runs. A bare-metal or dedicated-instance target has to be chosen before the headline number is quoted anywhere, and the harness has to stay portable from the start rather than be retrofitted.
- ~~One-way TSC offset~~ — **settled: θ = 5.5 ns, one-way handoff 105.5 ns** (§12). The standing rule is that a one-way latency is reported as the mean of both directions, since that is what cancels θ. The additive 68 ns floor is withdrawn with it.
- ~~Where the capacity knee is~~ — **settled at n=3: 128 Ki (8 MiB)** (§7, §12). Throughput ties with 64 Ki and dwell time breaks the tie by an order of magnitude. Re-measure once the consumer carries the LOB, since every figure behind this came from a consumer that only walks a counter.
- ~~The 48 ms at 16 MiB~~ — **not a transient and not proportional: it fell to 19.41 ms when `--events` doubled, while throughput rose outside the n=3 range** (§12). Mean batch, not capacity, predicts throughput across all thirteen runs. Capacity measurement is closed as over-measured relative to a target every resident size clears by 15-37x.
- ~~`full_stalls` counts episodes, not time~~ — **settled: the producer now accumulates stalled cycles** (§12), and the dwell figure immediately decided §7's capacity where the episode count had pointed the other way.
- Huge pages for the slot array (§7) — take them if free; the recomputed TLB cost is under 2 ns per event, so they do not decide anything.
- ~~Consumer spin strategy~~ — **settled: `_mm_pause()`.** It beats a tight spin by ~53 ns at p50 and `UMWAIT` C0.1 by ~36 ns at p50 and 4–5× at p99.9 (§11).
- ~~Cross-core TSC offset~~ — **settled: bounded inside ±40 ns with zero in every interval, so `clock_id` is `RDTSCP`** (§9, §11).
- ~~Capacity default~~ — **settled: 1 Mi for throughput runs, 64 Ki for latency runs** (§7). Whether it is a build-time constant or a runtime parameter is still open; it is in the header either way.
