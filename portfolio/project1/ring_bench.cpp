// ring_bench.cpp -- the ring from ring.hpp driven by two pinned threads in one
// process. No shared memory and no Rust yet, deliberately: this separates what
// the ring costs from what the process boundary costs, so that when the figure
// moves after sgm_open lands there is something to attribute the move to.
//
// Two modes measuring two different things:
//   --mode lat    paced producer, one event  per Acquire. Measures the handoff.
//   --mode tput   producer flat out, consumer batching. Measures capacity.
// Read every latency figure against DESIGN.md §11: on this host the one-way
// coherence floor is ~45 ns and an RDTSCP pair costs ~23 ns, so a raw number
// here is mostly instrument until it is well clear of those.

#include "bench_util.hpp"
#include "ring.hpp"

#include <immintrin.h>
#include <sys/mman.h>

#include <atomic>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <thread>
#include <type_traits>
#include <vector>

namespace {
using namespace bench;

// NOT the market event schema -- DESIGN.md §8 leaves that to its own contract.
// This is the smallest payload satisfying the four properties the ring fixes,
// carrying the two things a bench needs: a sequence number, so a gap or a
// reorder is detectable rather than silent, and the stamp §9 requires.
struct alignas(ring::kSlotBytes) BenchEvent
{
    uint64_t seq;
    uint64_t t_produce; // TSC, written immediately before publish()
    uint64_t pad[6];
};
static_assert(sizeof(BenchEvent) == ring::kSlotBytes, "one event is one slot");
static_assert(alignof(BenchEvent) == ring::kSlotBytes, "one event is one cache line");
static_assert(std::is_trivially_copyable_v<BenchEvent>, "a slot is published by a plain store");

struct Counters
{
    std::atomic<uint64_t> sent{0};
    std::atomic<uint64_t> recv{0};
    std::atomic<uint64_t> gaps{0};
    std::atomic<uint64_t> full_stalls{0};
    std::atomic<uint64_t> polls{0};
    std::atomic<uint64_t> queued{0}; // polls that found more than one event ready
    std::atomic<uint64_t> full_cycles{0};
};

// Paced so the ring stays near-empty. A producer running flat out fills the
// ring, and the consumer then measures queueing delay -- a figure that still
// looks small and has stopped meaning what its name says.
void produce(ring::Header *h, int cpu, uint64_t events, uint64_t period_cycles, bool stamp, Counters *c)
{
    if (!pin_to(cpu)) std::fprintf(stderr, "ring_bench: producer failed to pin to cpu %d\n", cpu);
    ring::Producer p(h);

    const uint64_t t0 = rdtscp_now();
    for (uint64_t i = 0; i < events; ++i)
    {
        if (period_cycles != 0)
        {
            const uint64_t deadline = t0 + i * period_cycles;
            while (rdtscp_now() < deadline) _mm_pause();
        }

        uint8_t *slot = p.claim();
        if (slot == nullptr)
        {
            // Episodes and dwell are different questions. Once the ring
            // saturates the producer emits one fresh episode per consumer
            // commit, so a count alone cannot separate many brief bumps from
            // one long stall -- and §5's drop-versus-backpressure policy turns
            // on the dwell, not the count.
            const uint64_t t_stall = rdtscp_now();
            c->full_stalls.fetch_add(1, std::memory_order_relaxed);
            do
            {
                _mm_pause();
                slot = p.claim();
            } while (slot == nullptr);
            c->full_cycles.fetch_add(rdtscp_now() - t_stall, std::memory_order_relaxed);
        }

        BenchEvent *e = reinterpret_cast<BenchEvent *>(slot);
        e->seq = i;
        // §9: stamp immediately before the Release store, so the interval
        // excludes every line above this one.
        e->t_produce = stamp ? rdtscp_now() : 0;
        p.publish();
    }

    c->sent.store(events, std::memory_order_relaxed);
    p.finish();
}

void consume(ring::Header *h, int cpu, bool measure, uint64_t max_batch, std::vector<uint64_t> *raw, Counters *c)
{
    if (!pin_to(cpu)) std::fprintf(stderr, "ring_bench: consumer failed to pin to cpu %d\n", cpu);
    ring::Consumer q(h);

    uint64_t expect = 0;
    uint64_t recv = 0;
    uint64_t nmeas = 0;
    uint64_t polls = 0;
    uint64_t queued = 0;

    while (true)
    {
        uint64_t n = q.available();
        if (n == 0)
        {
            // The producer publishes everything, then sets Exited with a
            // Release. Re-checking after seeing Exited closes the window where
            // the last publish landed between the two loads.
            if (h->prod.producer_state.load(std::memory_order_acquire) == static_cast<uint32_t>(ring::ProducerState::Exited) && q.available() == 0) break;
            _mm_pause();
            continue;
        }

        // §9: read the clock immediately after the Acquire succeeds.
        const uint64_t t_consume = rdtscp_now();
        ++polls;
        if (n > 1) ++queued;
        if (n > max_batch) n = max_batch;

        for (uint64_t k = 0; k < n; ++k)
        {
            const BenchEvent *e = reinterpret_cast<const BenchEvent *>(q.peek());
            if (e->seq != expect) c->gaps.fetch_add(1, std::memory_order_relaxed);
            expect = e->seq + 1;
            // Only the first event of a batch was waited for; the rest were
            // already in the ring and their interval would be queueing.
            if (measure && k == 0 && nmeas < raw->size()) (*raw)[nmeas++] = t_consume - e->t_produce;
            ++recv;
            q.pop();
        }

        // An unbounded batch amortizes the cross-core read further but holds
        // read_idx back, which the producer sees as the ring being full. The
        // cap is where that trade gets made.
        q.commit();
    }

    c->recv.store(recv, std::memory_order_relaxed);
    c->polls.store(polls, std::memory_order_relaxed);
    c->queued.store(queued, std::memory_order_relaxed);
    if (measure) raw->resize(nmeas);
}

} // namespace

int main(int argc, char **argv)
{
    const char *mode = "lat";
    uint64_t capacity = 65536;
    uint64_t events = 2000000;
    uint64_t rate = 1000000; // msg/s, latency mode only
    uint64_t max_batch = 1024;
    int producer_cpu = 0;
    int consumer_cpu = 2;

    for (int i = 1; i < argc; ++i)
    {
        if (std::strcmp(argv[i], "--mode") == 0 && i + 1 < argc) mode = argv[++i];
        else if (std::strcmp(argv[i], "--capacity") == 0 && i + 1 < argc)
            capacity = std::strtoull(argv[++i], nullptr, 10);
        else if (std::strcmp(argv[i], "--events") == 0 && i + 1 < argc)
            events = std::strtoull(argv[++i], nullptr, 10);
        else if (std::strcmp(argv[i], "--rate") == 0 && i + 1 < argc)
            rate = std::strtoull(argv[++i], nullptr, 10);
        else if (std::strcmp(argv[i], "--batch") == 0 && i + 1 < argc)
            max_batch = std::strtoull(argv[++i], nullptr, 10);
        else if (std::strcmp(argv[i], "--producer-cpu") == 0 && i + 1 < argc)
            producer_cpu = std::atoi(argv[++i]);
        else if (std::strcmp(argv[i], "--consumer-cpu") == 0 && i + 1 < argc)
            consumer_cpu = std::atoi(argv[++i]);
        else
        {
            std::printf("unknown argument: %s\n", argv[i]);
            return 2;
        }
    }

    const bool lat = std::strcmp(mode, "lat") == 0;
    if (!lat && std::strcmp(mode, "tput") != 0)
    {
        std::printf("--mode must be lat or tput\n");
        return 2;
    }

    const double tsc_hz = calibrate_tsc_hz(100000000ull);
    const double ns_per_cycle = 1e9 / tsc_hz;

    const size_t bytes = ring::segment_bytes(capacity);
    // MAP_POPULATE prefaults the whole segment. Without it the first lap of the
    // ring takes a page fault every 64 slots, and those land squarely in the
    // p99.9 this batch exists to report.
    void *base = mmap(nullptr, bytes, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS | MAP_POPULATE, -1, 0);
    if (base == MAP_FAILED)
    {
        std::perror("mmap");
        return 1;
    }

    ring::Header *h = ring::init(base, capacity, ring::ClockId::Rdtscp);
    // Attach as the router will. In one process this cannot fail; it runs here
    // so the path that must abort on a stale segment is a path the bench
    // actually exercises rather than one nothing has ever taken.
    // clang-format off
    ring::attach(base, capacity, ring::ClockId::Rdtscp);
    std::printf(
        "ring_bench -- mode=%s capacity=%llu (%.1f MiB) events=%llu cpu %d -> %d, TSC %.4f GHz\n",
        mode, static_cast<unsigned long long>(capacity),
        static_cast<double>(bytes) / (1024.0 * 1024.0),
        static_cast<unsigned long long>(events),
        producer_cpu, consumer_cpu, tsc_hz / 1e9
    );
    if (lat) std::printf("            paced at %llu msg/s, batch 1\n", static_cast<unsigned long long>(rate));
    else     std::printf("            unpaced, batch cap %llu\n", static_cast<unsigned long long>(max_batch));
    // clang-format on
    const uint64_t period = lat ? static_cast<uint64_t>(tsc_hz / static_cast<double>(rate)) : 0;
    const uint64_t batch = lat ? 1 : max_batch;

    std::vector<uint64_t> raw(lat ? events : 1, 0);
    Counters c;

    const uint64_t wall0 = now_ns(CLOCK_MONOTONIC);
    std::thread tc(consume, h, consumer_cpu, lat, batch, &raw, &c);
    std::thread tp(produce, h, producer_cpu, events, period, lat, &c);
    tp.join();
    tc.join();
    const uint64_t wall1 = now_ns(CLOCK_MONOTONIC);

    const uint64_t dropped = h->prod.dropped_count.load(std::memory_order_relaxed);
    const uint64_t recv = c.recv.load(std::memory_order_relaxed);
    const uint64_t gaps = c.gaps.load(std::memory_order_relaxed);
    const uint64_t polls = c.polls.load(std::memory_order_relaxed);
    const uint64_t queued = c.queued.load(std::memory_order_relaxed);
    // clang-format off
    std::printf(
        "  sent=%llu recv=%llu gaps=%llu dropped=%llu full-stalls=%llu\n",
        static_cast<unsigned long long>(events),
        static_cast<unsigned long long>(recv),
        static_cast<unsigned long long>(gaps),
        static_cast<unsigned long long>(dropped),
        static_cast<unsigned long long>(c.full_stalls.load(std::memory_order_relaxed))
    );
    // clang-format on
    if (lat)
    {
        Hist hist;
        for (uint64_t v : raw) hist.add(static_cast<uint64_t>(static_cast<double>(v) * ns_per_cycle));
        report("produce -> consume", hist);
        // If this is not near zero the producer is outrunning the consumer and
        // the figure above is queueing delay, not handoff latency.
        // clang-format off
        std::printf(
            "  %-30s polls that found >1 event ready: %.3f%% (%llu of %llu)\n", "",
            polls ? 100.0 * static_cast<double>(queued) / static_cast<double>(polls) : 0.0,
            static_cast<unsigned long long>(queued), static_cast<unsigned long long>(polls)
        );
        std::printf("  %-30s reference: RDTSCP pair ~23 ns, one-way coherence floor ~45 ns (DESIGN.md §11)\n", "");
    }
    else
    {
        const double secs = static_cast<double>(wall1 - wall0) / 1e9;
        std::printf(
            "  %-30s %.2f s, %.2f M msg/s, %.1f ns/msg, mean batch %.1f\n", "",
            secs, static_cast<double>(recv) / secs / 1e6,
            secs * 1e9 / static_cast<double>(recv),
            polls ? static_cast<double>(recv) / static_cast<double>(polls) : 0.0
        );
        const double stall_ns = static_cast<double>(c.full_cycles.load(std::memory_order_relaxed)) * ns_per_cycle;
        std::printf(
            "  %-30s producer blocked on full: %.3f%% of run (%.2f ms)\n", "",
            100.0 * stall_ns / (secs * 1e9), stall_ns / 1e6
        );
    }

    // §5: silent loss is the failure mode that destroys a backtest's
    // credibility and is undetectable after the fact. Say it here or nowhere.
    const bool valid = (dropped == 0) && (gaps == 0) && (recv == events);
    std::printf("  RUN %s\n", valid ? "VALID" : "INVALID");

    munmap(base, bytes);
    return valid ? 0 : 1;
}