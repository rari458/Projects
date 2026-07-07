// benchmarks/BacktesterBenchmark.cpp
//
// Microbenchmarks for the Backtester hot path (the on_market_data tick loop).
// Establishes a throughput BASELINE before any optimization. Behaviour is pinned
// separately by the characterization tests, so we may optimize freely as long as
// those 16 goldens stay green.

#include <benchmark/benchmark.h>

#include <cmath>
#include <vector>

#include "Backtester.h"

namespace {

// Same RNG-free series as the characterization test, for comparable numbers.
std::vector<double> MakeSeries(int n) {
    std::vector<double> prices;
    prices.reserve(n);
    double price = 100.0;
    for (int i = 0; i < n; ++i) {
        const double drift = 0.0005 * price;
        const double wiggle = 2.0 * std::sin(i * 0.30) + 0.7 * std::cos(i * 0.11);
        price += drift + wiggle;
        if (price < 1.0) price = 1.0;
        prices.push_back(price);
    }
    return prices;
}

// A fresh engine per iteration (state accumulates per tick, so reusing one would
// drift). Construction cost is negligible against n ticks and is reported as
// throughput via SetItemsProcessed.
void RunStrategy(benchmark::State& state, const char* strategy) {
    const int n = static_cast<int>(state.range(0));
    const std::vector<double> closes = MakeSeries(n);

    for (auto _ : state) {
        Backtester engine(100000.0, strategy, 1.0);
        engine.set_quiet(true);
        for (int t = 0; t < n; ++t) {
            const double c = closes[t];
            engine.on_market_data("TEST", static_cast<double>(t), c, c, c, c);
        }
        benchmark::DoNotOptimize(engine.get_total_equity());
    }

    state.SetItemsProcessed(state.iterations() * n);  // -> ticks/sec
}

}  // namespace

BENCHMARK_CAPTURE(RunStrategy, ema, "EMA")->Arg(1000)->Arg(10000)->Unit(benchmark::kMicrosecond);
BENCHMARK_CAPTURE(RunStrategy, macd, "MACD")->Arg(1000)->Arg(10000)->Unit(benchmark::kMicrosecond);

BENCHMARK_MAIN();