// bench_util.hpp -- histogram, clocks and CPU pinning shared by the benches.
//
// Both benches must compute percentiles identically. DESIGN.md §11 is the
// baseline every ring figure is read against, and a divergence in how the two
// binaries bucket their samples would make that comparison quietly wrong.

#pragma once

#include <immintrin.h>
#include <pthread.h>
#include <sched.h>
#include <time.h>

#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <vector>

namespace bench
{
// ---------------------------------------------------------------- histogram
// 1 ns per bucket up to 64 us, exact values kept above that. Bucket width equals
// the clock's own resolution, so percentiles inside the linear range are exact
// rather than interpolated, and rare outliers do not distort the scale.
constexpr size_t kLinearBuckets = 65536;

class Hist
{
    public:
        Hist() : bucket_(kLinearBuckets, 0) { overflow_.reserve(1u << 16); }

        void add(uint64_t v)
        {
            ++n_;
            sum_ += v;
            if (v < min_) min_ = v;
            if (v > max_) max_ = v;
            if (v < kLinearBuckets) ++bucket_[v];
            else
            {
                overflow_.push_back(v);
                sorted_ = false;
            }
        }

        uint64_t count() const { return n_; }
        uint64_t min() const { return n_ ? min_ : 0; }
        uint64_t max() const { return max_; }
        double mean() const { return n_ ? static_cast<double>(sum_) / static_cast<double>(n_) : 0.0; }

        // Number of samples at or above a threshold -- used to count preemptions.
        uint64_t count_at_least(uint64_t threshold)
        {
            uint64_t c = 0;
            for (size_t i = threshold; i < kLinearBuckets; ++i) c += bucket_[i];
            for (uint64_t v : overflow_) 
                if (v >= threshold) ++c;
            return c;
        }

        uint64_t percentile(double p)
        {
            if (n_ == 0) return 0;
            uint64_t target = static_cast<uint64_t>(p * static_cast<double>(n_));
            if (target >= n_) target = n_ - 1;
            uint64_t acc = 0;
            for (size_t i = 0; i < kLinearBuckets; ++i)
            {
                acc += bucket_[i];
                if (acc > target) return static_cast<uint64_t>(i);
            }
            if (overflow_.empty()) return max_;
            if (!sorted_)
            {
                std::sort(overflow_.begin(), overflow_.end());
                sorted_ = true;
            }
            uint64_t idx = target - acc;
            if (idx >= overflow_.size()) idx = overflow_.size() - 1;
            return overflow_[static_cast<size_t>(idx)];
        }

    private:
        std::vector<uint64_t> bucket_;
        std::vector<uint64_t> overflow_;
        uint64_t n_ = 0;
        uint64_t sum_ = 0;
        uint64_t min_ = UINT64_MAX;
        uint64_t max_ = 0;
        bool sorted_ = true;
};

inline void report(const char* label, Hist& h)
{
    std::printf(
        " %-30s n=%-11llu min=%6llu p50=%6llu p99=%7llu p99.9=%8llu max=%10llu\n",
        label,
        static_cast<unsigned long long>(h.count()),
        static_cast<unsigned long long>(h.min()),
        static_cast<unsigned long long>(h.percentile(0.50)),
        static_cast<unsigned long long>(h.percentile(0.99)),
        static_cast<unsigned long long>(h.percentile(0.999)),
        static_cast<unsigned long long>(h.max())
    );
}

// -------------------------------------------------------------------- clocks
inline uint64_t now_ns(clockid_t clk) 
{
    timespec ts;
    clock_gettime(clk, &ts);
    return static_cast<uint64_t>(ts.tv_sec) * 1000000000ull + static_cast<uint64_t>(ts.tv_nsec);
}

inline uint64_t rdtscp_now()
{
    unsigned aux;
    return __rdtscp(&aux);
}

inline bool pin_to(int cpu)
{
    cpu_set_t set;
    CPU_ZERO(&set);
    CPU_SET(cpu, &set);
    return pthread_setaffinity_np(pthread_self(), sizeof(set), &set) == 0;
}

// TSC frequency against CLOCK_MONOTONIC. Run more than once: a figure that moves
// between runs means the TSC is not usable as a timebase here, whatever the
// constant_tsc/nonstop_tsc flags claim.
inline double calibrate_tsc_hz(uint64_t window_ns)
{
    const uint64_t t0 = now_ns(CLOCK_MONOTONIC);
    const uint64_t c0 = rdtscp_now();
    while (now_ns(CLOCK_MONOTONIC) - t0 < window_ns) _mm_pause();
    const uint64_t c1 = rdtscp_now();
    const uint64_t t1 = now_ns(CLOCK_MONOTONIC);
    return static_cast<double>(c1 - c0) * 1e9 / static_cast<double>(t1 - t0);
}
} // namespace bench