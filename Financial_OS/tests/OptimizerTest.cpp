// tests/OptimizerTest.cpp

#include <gtest/gtest.h>
#include <cmath>
#include <numeric>
#include <string>
#include <thread>
#include "../include/Optimizer.h"

namespace {

Optimizer MakeOptimizer() {
    Optimizer opt;
    for (int a = 0; a < 5; ++a) {
        std::vector<double> returns;
        for (int t = 0; t < 252; ++t) {
            returns.push_back(0.01 * std::sin((a + 1) * t * 0.05) + 0.002 * std::cos(t * 0.13));
        }
        opt.add_asset("ASSET" + std::to_string(a), returns);
    }
    return opt;
}

}  // namespace

TEST(OptimizerTest, UsableCpusStaysWithinTheMachine) {
    const unsigned int n = Optimizer::usable_cpus();
    EXPECT_GE(n, 1u);
    EXPECT_LE(n, std::max(1u, std::thread::hardware_concurrency()));
}

TEST(OptimizerTest, EveryThreadCountReturnsAFullyInvestedPortfolio) {
    // 0 = all usable CPUs, 1 = inline, 2 = a cap, 1000 = more than any machine has.
    Optimizer opt = MakeOptimizer();
    for (unsigned int threads : {0u, 1u, 2u, 1000u}) {
        const OptimizationResult r = opt.optimize_sharpe_ratio(5000, 0.02, threads);
        ASSERT_EQ(r.optimal_weights.size(), 5u) << "threads=" << threads;
        const double total = std::accumulate(r.optimal_weights.begin(), r.optimal_weights.end(), 0.0);
        EXPECT_NEAR(total, 1.0, 1e-9) << "threads=" << threads;
        EXPECT_TRUE(std::isfinite(r.sharpe_ratio)) << "threads=" << threads;
    }
}
