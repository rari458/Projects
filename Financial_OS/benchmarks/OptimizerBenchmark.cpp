// benchmarks/OptimizerBenchmark.cpp

#include <benchmark/benchmark.h>
#include <string>
#include "../include/Optimizer.h"

namespace {

Optimizer MakeOptimizer(int n_assets, int n_periods) {
    Optimizer opt;
    for (int a = 0; a < n_assets; ++a) {
        std::vector<double> returns;
        returns.reserve(n_periods);
        for (int t = 0; t < n_periods; ++t) {
            const double wiggle = 0.01 * std::sin((a + 1) * t * 0.05) + 0.002 * std::cos(t * 0.13);
            returns.push_back(wiggle);
        }
        opt.add_asset("ASSET" + std::to_string(a), returns);
    }
    return opt;
}

void RunOptimize(benchmark::State& state, unsigned int num_threads) {
    const int num_simulations = static_cast<int>(state.range(0));
    Optimizer opt = MakeOptimizer(10, 252);

    for (auto _ : state) {
        auto result = opt.optimize_sharpe_ratio(num_simulations, 0.02, num_threads);
        benchmark::DoNotOptimize(result.sharpe_ratio);
    }

    state.SetItemsProcessed(state.iterations() * num_simulations);
}

} // namespace

BENCHMARK_CAPTURE(RunOptimize, serial_1_thread, 1u)->Arg(10000)->Arg(100000)->Unit(benchmark::kMillisecond);
BENCHMARK_CAPTURE(RunOptimize, parallel_auto, 0u)->Arg(10000)->Arg(100000)->Unit(benchmark::kMillisecond);