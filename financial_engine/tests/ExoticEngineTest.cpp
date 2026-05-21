#include <gtest/gtest.h>
#include <fmt/core.h>
#include <vector>
#include "../include/ExoticBSEngine.h"
#include "../include/PathDependentAsian.h"
#include "../include/Payoff.h"
#include "../include/Parameters.h"
#include "../include/MCStatistics.h"
#include "../include/Random.h"
#include "../include/AntiThetic.h"
#include <cmath>

double BSPrice(double S, double K, double r, double v, double T) {
    double d1 = (std::log(S/K) + (r + 0.5 * v * v) * T) / (v * std::sqrt(T));
    double d2 = d1 - v * std::sqrt(T);
    auto N = [](double x) { return 0.5 * std::erfc(-x * std::sqrt(0.5)); };
    return S * N(d1) - K * std::exp(-r * T) * N(d2);
}

TEST(ExoticEngineTest, AsianReducedToEuropean) {
    double Spot = 100.0;
    double Strike = 100.0;
    double Vol = 0.2;
    double Rate = 0.05;
    double Div = 0.0;
    double Expiry = 1.0;
    unsigned long Paths = 100000;

    ParametersConstant VolParam(Vol);
    ParametersConstant RateParam(Rate);
    ParametersConstant DivParam(Div);
    PayoffCall ThePayoff(Strike);

    std::vector<double> Times = { Expiry };
    PathDependentAsian TheAsian(Times, Expiry, ThePayoff);

    StatisticsMean stats;
    RandomMersenne gen(1);
    AntiThetic antiGen(gen);

    ExoticBSEngine TheEngine(TheAsian, RateParam, DivParam, VolParam, Spot);
    TheEngine.DoSimulation(stats, Paths, antiGen);

    double mcPrice = stats.GetResultsSoFar()[0][0];
    double exactPrice = BSPrice(Spot, Strike, Rate, Vol, Expiry);

    fmt::print("\n[Exotic Engine Check]\n");
    fmt::print("Asian(European-like) MC Price: {:.5f}\n", mcPrice);
    fmt::print("Exact BS Price:              {:.5f}\n", exactPrice);

    EXPECT_NEAR(mcPrice, exactPrice, 0.1);
}