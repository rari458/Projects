#include <gtest/gtest.h>
#include <fmt/core.h>
#include "../include/SimpleMC.h"
#include "../include/Payoff.h"
#include "../include/VanillaOption.h"
#include "../include/MCStatistics.h"
#include "../include/Random.h"
#include <cmath>

double BlackScholesCall(double S, double K, double r, double v, double T) {
    double d1 = (std::log(S/K) + (r + 0.5 * v * v) * T) / (v * std::sqrt(T));
    double d2 = d1 - v * std::sqrt(T);
    auto N = [](double x) { return 0.5 * std::erfc(-x * std::sqrt(0.5)); };
    return S * N(d1) - K * std::exp(-r * T) * N(d2);
}

TEST(MonteCarloTest, ConvergenceToBlackScholes) {
    double spot = 100.0;
    double strike = 100.0;
    double expiry = 1.0;
    double vol = 0.2;
    double r = 0.05;
    unsigned long paths = 1'000'000;

    PayoffCall callPayoff(strike);
    VanillaOption theOption(callPayoff, expiry);
    StatisticsMean gatherer;

    RandomMersenne generator(1);
    SimpleMonteCarlo(theOption, spot, vol, r, paths, gatherer, generator);

    double mcPrice = gatherer.GetResultsSoFar()[0][0];
    double bsPrice = BlackScholesCall(spot, strike, r, vol, expiry);

    EXPECT_NEAR(mcPrice, bsPrice, 0.1);
}