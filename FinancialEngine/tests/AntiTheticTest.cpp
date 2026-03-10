#include <gtest/gtest.h>
#include <fmt/core.h>
#include <cmath>
#include "../include/SimpleMC.h"
#include "../include/VanillaOption.h"
#include "../include/MCStatistics.h"
#include "../include/Random.h"
#include "../include/AntiThetic.h"

double BSCall(double S, double K, double r, double v, double T) {
    double d1 = (std::log(S/K) + (r + 0.5 * v * v) * T) / (v * std::sqrt(T));
    double d2 = d1 - v * std::sqrt(T);
    auto N = [](double x) { return 0.5 * std::erfc(-x * std::sqrt(0.5)); };
    return S * N(d1) - K * std::exp(-r * T) * N(d2);
}

TEST(MonteCarloTest, VarianceReductionTest) {
    double spot = 100.0;
    double strike = 100.0;
    double expiry = 1.0;
    double vol = 0.2;
    double r = 0.05;
    unsigned long paths = 5000;

    PayoffCall callPayoff(strike);
    VanillaOption theOption(callPayoff, expiry);
    double exactPrice = BSCall(spot, strike, r, vol, expiry);

    StatisticsMean stats1;
    RandomMersenne gen1(1);
    SimpleMonteCarlo(theOption, spot, vol, r, paths, stats1, gen1);
    double price1 = stats1.GetResultsSoFar()[0][0];
    double error1 = std::abs(price1 - exactPrice);

    StatisticsMean stats2;
    RandomMersenne innerGen(1);
    AntiThetic gen2(innerGen);

    SimpleMonteCarlo(theOption, spot, vol, r, paths, stats2, gen2);
    double price2 = stats2.GetResultsSoFar()[0][0];
    double error2 = std::abs(price2 - exactPrice);

    fmt::print("\n[Variance Reduction Check]\n");
    fmt::print("Standard Error: {:.5f} (Price: {:.5f})\n", error1, price1);
    fmt::print("Antithetic Error: {:.5f} (Price: {:.5f})\n", error2, price2);

    EXPECT_NEAR(price2, exactPrice, 0.2);
}