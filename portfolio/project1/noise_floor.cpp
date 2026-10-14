// noise_floor.cpp -- environment characterization for the ultra-low-latency engine.
//
// Measures the measuring apparatus before anything is built on top of it:
//  1. clock read cost and resolution (CLOCK_MONOTONIC, CLOCK_MONOTONIC_RAW, RDTSCP)
//  2. core-to-core cache line handoff latency, swept over every vCPU pair
//  3. scheduler jitter on a pinned spin loop
//
// Every later latency figure in this project is reported against these numbers.
// Reported topology on this host is synthesized by the hypervisor, so the pair
// sweep in test 2 is the only way to find out what the vCPU numbering means.
//
// Usage: ./noise_floor [--jitter-seconds N] [--pin-cpu N] [--pairs-iters N]

#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif

#include <immintrin.h>
#include <pthread.h>
#include <sched.h>
#include <time.h>

#include <algorithm>
#include <atomic>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <thread>
#include <vector>
#include "bench_util.hpp"

namespace
{
using namespace bench;
// ------------------------------------------------------ test 1: clock cost
// samples land in a pre-sized buffer so the measured region stays a pair of
// clock reads and one store; the histogram is filled afterwards.
void bench_clock(const char* name, clockid_t clk, size_t iters, std::vector<uint64_t>& raw)
{
    for (size_t i = 0; i < 100000; ++i) (void)now_ns(clk);
    for (size_t i = 0; i < iters; ++i)
    {
        const uint64_t t0 = now_ns(clk);
        const uint64_t t1 = now_ns(clk);
        raw[i] = t1 - t0;
    }

    Hist h;
    uint64_t zeros = 0;
    for (size_t i = 0; i < iters; ++i)
    {
        if (raw[i] == 0) ++zeros;
        h.add(raw[i]);
    }
    report(name, h);
    std::printf(
        "  %-30s zero-delta %.2f%%  (a high share means the clock is coarser than one call)\n",
        "", 100.0 * static_cast<double>(zeros) / static_cast<double>(iters)
    );
}

void bench_rdtscp(size_t iters, double tsc_hz, std::vector<uint64_t>& raw)
{
    for (size_t i = 0; i < 100000; ++i) (void)rdtscp_now();
    for (size_t i = 0; i < iters; ++i)
    {
        const uint64_t c0 = rdtscp_now();
        const uint64_t c1 = rdtscp_now();
        raw[i] = c1 - c0;
    }

    Hist h;
    const double ns_per_cycle = 1e9 / tsc_hz;
    for (size_t i = 0; i < iters; ++i) h.add(static_cast<uint64_t>(static_cast<double>(raw[i]) * ns_per_cycle));
    report("RDTSCP", h);
}

// ------------------------------------- test 2: core-to-core cache line handoff

struct alignas(128) PingPong
{
    std::atomic<uint64_t> seq{0};
    uint64_t stamp{0};  // responder's TSC; same line as seq, so it costs no extra transfer
    char pad[128 - sizeof(std::atomic<uint64_t>)]{};
};

enum class Spin
{
    Pause,
    Tight,
    Umwait
};

const char* spin_name(Spin m)
{
    switch (m)
    {
        case Spin::Pause:   return "PAUSE";
        case Spin::Tight:   return "tight";
        case Spin::Umwait:  return "UMWAIT";
    }
    return "?";
}

// Branch on the spin strategy outside the loop, never inside it.
//
// UMWAIT does not spin at all: it parks the logical core until the monitored
// line is written, so it pays neither PAUSE's granularity nor the memory-order
// machine clear a hammered spin loop takes on exit. C0.1 (bit 0 of the first
// operand) is the low-wakeup-latency state; C0.2 saves more power and wakes
// slower, which is the wrong trade here.
inline void spin_until(const std::atomic<uint64_t>& seq, uint64_t want, Spin mode)
{
    switch (mode)
    {
        case Spin::Pause:
            while (seq.load(std::memory_order_acquire) != want) _mm_pause();
            return;
        case Spin::Tight:
            while (seq.load(std::memory_order_acquire) != want) { }
            return;
        case Spin::Umwait:
#ifdef __WAITPKG__
        while (seq.load(std::memory_order_acquire) != want)
        {
            _umonitor(const_cast<std::atomic<uint64_t>*>(&seq));
            // Re-check after arming. A store landing between the load above
            // and the UMONITOR would otherwise be waited on after the fact,
            // and the wait would only end on the deadline.
            if (seq.load(std::memory_order_acquire) == want) return;
            _umwait(1, __rdtsc() + 100000);     // ~35 us deadline; re-arm on timeout
        }
#else
        while (seq.load(std::memory_order_acquire) != want) _mm_pause();
#endif
        return;
    }
}

// Cost of one PAUSE. 16 per sample amortizes the ~11 ns clock pair away. If this
// is tens of nanoseconds, a value arriving mid-PAUSE is not observed until the
// PAUSE retires, and that delay is inside every figure test 2 reports.
void bench_pause(size_t iters, double tsc_hz)
{
    Hist h;
    const double ns_per_cycle = 1e9 / tsc_hz;
    for (size_t i = 0; i < 10000; ++i) _mm_pause();
    for (size_t i = 0; i < iters; ++i)
    {
        const uint64_t c0 = rdtscp_now();
        for (int k = 0; k < 16; ++k) _mm_pause();
        const uint64_t c1 = rdtscp_now();
        h.add(static_cast<uint64_t>(static_cast<double>(c1 - c0) * ns_per_cycle / 16.0));
    }
    report("per-PAUSE", h);
}

void responder(PingPong* pp, int cpu, size_t iters, std::atomic<int>* landed, Spin mode)
{
    const bool ok = pin_to(cpu);
    landed->store(ok ? sched_getcpu() : -1, std::memory_order_release);
    const bool stamp = (mode != Spin::Umwait);
    for (size_t i = 1; i <= iters; ++i)
    {
        spin_until(pp->seq, 2 * i - 1, mode);
        // UMONITOR arms on a cache-line granule and stamp shares seq's line, so
        // writing it here would wake the initiator one store early and that wake
        // would be measured as latency. The offset it bounds is settled anyway.
        if (stamp) pp->stamp = rdtscp_now();                    // released by the store below
        pp->seq.store(2 * i, std::memory_order_release);
    }
}

// Round trip is measured with RDTSCP rather than clock_gettime: the handoff is
// expected to be tens of nanoseconds, where a clock call is a large share of the
// figure rather than a rounding error.
//
// The responder's own stamp bounds the cross-core TSC offset. With B's clock at
// A's + theta and both one-way delays non-negative, theta lies in
// [-min(c1 - t1), +min(t1 - c0)]. An interval straddling zero means the two cores
// share an origin; one that excludes it means every cross-core timestamp in this
// project needs correcting by that amount.
void bench_pair(int cpu_a, int cpu_b, size_t iters, size_t warmup, double tsc_hz, Spin mode)
{
    PingPong pp;
    std::atomic<int> landed_b{-2};
    std::vector<uint64_t> raw(iters, 0);
    std::vector<uint64_t> out(iters, 0);

    std::thread t(responder, &pp, cpu_b, iters + warmup, &landed_b, mode);

    const bool ok_a = pin_to(cpu_a);
    const int landed_a = ok_a ? sched_getcpu() : -1;
    while (landed_b.load(std::memory_order_acquire) == -2) _mm_pause();

    for (size_t i = 1; i <= iters + warmup; ++i)
    {
        const uint64_t c0 = rdtscp_now();
        pp.seq.store(2 * i - 1, std::memory_order_release);
        spin_until(pp.seq, 2 * i, mode);
        const uint64_t c1 = rdtscp_now();
        const uint64_t t1 = pp.stamp;
        if (i > warmup)
        {
            raw[i - warmup - 1] = c1 - c0;
            out[i - warmup - 1] = t1 - c0;                      // meaningless in UMWAIT mode; not printed
        }
    }
    t.join();

    Hist rtt;
    const double ns_per_cycle = 1e9 / tsc_hz;
    int64_t min_out = INT64_MAX;
    int64_t min_back = INT64_MAX;
    for (size_t i = 0; i < iters; ++i)
    {
        rtt.add(static_cast<uint64_t>(static_cast<double>(raw[i]) * ns_per_cycle));
        const int64_t o = static_cast<int64_t>(out[i]);         // signed: t1 may precede c0
        const int64_t b = static_cast<int64_t>(raw[i]) - o;
        if (o < min_out) min_out = o;
        if (b < min_back) min_back = b;
    }

    char label[64];
    std::snprintf(
        label, sizeof(label), "cpu %2d <-> %2d  (ran on %d,%d)",
        cpu_a, cpu_b, landed_a, landed_b.load(std::memory_order_acquire)
    );
    char offset[48];
    if (mode == Spin::Umwait)
    {
        std::snprintf(offset, sizeof(offset), "tsc-offset n/a");
    }
    else
    {
        std::snprintf(
            offset, sizeof(offset), "tsc-offset in [%+.0f, %+.0f]",
            -static_cast<double>(min_back) * ns_per_cycle,
            static_cast<double>(min_out) * ns_per_cycle
        );
    }
    std::printf(
        "  %-30s n=%-1llu p50=%6llu p99=%7llu p99.9=%8llu  one-way p50=%llu  %s\n",
        label,
        static_cast<unsigned long long>(rtt.count()),
        static_cast<unsigned long long>(rtt.percentile(0.50)),
        static_cast<unsigned long long>(rtt.percentile(0.99)),
        static_cast<unsigned long long>(rtt.percentile(0.999)),
        static_cast<unsigned long long>(rtt.percentile(0.50) / 2),
        offset
    );
}

// ------------------------------------------------- test 3: scheduler jitter

// The histogram is filled inside the loop here -- billions of samples cannot be
// buffered. That adds a branch and an increment to every gap, which matters for
// the p50 and not at all for the tail, and the tail is the reason this test runs.
void bench_jitter(int cpu, double seconds)
{
    if (!pin_to(cpu)) std::printf("  pinning to cpu %d FAILED -- jitter figures are meaningless\n", cpu);
    std::printf("  pinned to cpu %d, running on cpu %d\n", cpu, sched_getcpu());

    Hist h;
    const uint64_t end = now_ns(CLOCK_MONOTONIC) + static_cast<uint64_t>(seconds * 1e9);
    uint64_t prev = now_ns(CLOCK_MONOTONIC);
    while (prev < end)
    {
        const uint64_t cur = now_ns(CLOCK_MONOTONIC);
        h.add(cur - prev);
        prev = cur;
    }

    report("spin-loop gap", h);
    std::printf(
        "  %-30s >10us: %llu   >100us: %llu   >1ms: %llu   (preemptions)\n",
        "",
        static_cast<unsigned long long>(h.count_at_least(10000)),
        static_cast<unsigned long long>(h.count_at_least(100000)),
        static_cast<unsigned long long>(h.count_at_least(1000000))
    );
    std::printf("  %-30s migrated to cpu %d by the end\n", "", sched_getcpu());
}

}    // namespace

int main(int argc, char** argv)
{
    double jitter_seconds = 10.0;
    int pin_cpu = 0;
    size_t pair_iters = 200000;

    for (int i = 1; i < argc; ++i) {
        if (std::strcmp(argv[i], "--jitter-seconds") == 0 && i + 1 < argc) {
            jitter_seconds = std::atof(argv[++i]);
        } else if (std::strcmp(argv[i], "--pin-cpu") == 0 && i + 1 < argc) {
            pin_cpu = std::atoi(argv[++i]);
        } else if (std::strcmp(argv[i], "--pair-iters") == 0 && i + 1 < argc) {
            pair_iters = static_cast<size_t>(std::atoi(argv[++i]));
        } else {
            std::printf("Unknown argument: %s\n", argv[i]);
            return 2;
        }
    }

    const unsigned ncpu = std::thread::hardware_concurrency();
    std::printf("noise_floor -- all figures in nanoseconds, %u vCPUs visible\n\n", ncpu);

    std::printf("== 0. TSC calibration ==\n");
    const double hz1 = calibrate_tsc_hz(100000000ull);
    const double hz2 = calibrate_tsc_hz(100000000ull);
    std::printf("  run 1: %.4f GHz\n  run 2: %.4f GHz\n  drift: %.4f%%\n\n", hz1 / 1e9, hz2 / 1e9, 100.0 * (hz2 - hz1) / hz1);
    const double tsc_hz = 0.5 * (hz1 + hz2);

    std::printf("== 1. clock read cost / resolution ==\n");
    {
        const size_t iters = 1000000;
        std::vector<uint64_t> raw(iters, 0);
        bench_clock("CLOCK_MONOTONIC", CLOCK_MONOTONIC, iters, raw);
        bench_clock("CLOCK_MONOTONIC_RAW", CLOCK_MONOTONIC_RAW, iters, raw);
        bench_rdtscp(iters, tsc_hz, raw);
    }
    std::printf("\n");

    std::printf("== 2a. PAUSE cost ==\n");
    bench_pause(200000, tsc_hz);
    std::printf("\n");

    const Spin modes[] = {Spin::Pause, Spin::Tight, Spin::Umwait};
    const char* tags[] = {"2b", "2c", "2d"};
    for (int m = 0; m < 3; ++m)
    {
#ifndef __WAITPKG__
        if (modes[m] == Spin::Umwait)
        {
            std::printf("== 2d. UMWAIT: not compiled in, __WAITPKG__ undefined ==\n\n");
            continue;
        }
#endif
        std::printf(
            "== %s. core-to-core handoff, %s spin, cpu %d vs every other vCPU ==\n",
            tags[m], spin_name(modes[m]), pin_cpu
        );
        for (unsigned peer = 0; peer < ncpu; ++peer)
        {
            if (static_cast<int>(peer) == pin_cpu) continue;
            bench_pair(pin_cpu, static_cast<int>(peer), pair_iters, 20000, tsc_hz, modes[m]);
        }
        std::printf("\n");
    }

    std::printf("== 3. scheduler jitter, %.1f s pinned spin ==\n", jitter_seconds);
    bench_jitter(pin_cpu, jitter_seconds);

    return 0;
}