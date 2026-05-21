#include <gtest/gtest.h>
#include <fmt/core.h>
#include "../include/SimpleMC.h"
#include "../include/BinomialTree.h"
#include "../include/BlackScholesFormulas.h"
#include "../include/NumericalGreeks.h"
#include "../include/Payoff.h"
#include "../include/Parameters.h"
#include "../include/VanillaOption.h"
#include "../include/MCStatistics.h"
#include "../include/Random.h"
#include "../include/AntiThetic.h"

double BSDelta(double S, double K, double r, double v, double T) {
    double d1 = (std::log(S/K) + (r + 0.5 * v *v) * T) / (v * std::sqrt(T));
    return 0.5 * std::erfc(-d1 * std::sqrt(0.5));
}

double BSGamma(double S, double K, double r, double v, double T) {
    double d1 = (std::log(S/K) + (r + 0.5 * v * v) * T) / (v * std::sqrt(T));
    return (std::exp(-0.5 * d1 * d1) / std::sqrt(2 * M_PI)) / (S * v * std::sqrt(T));
}

TEST(RiskEngineTest, GreeksComparision) {
    double Spot = 100.0;
    double Strike = 100.0;
    double r = 0.05;
    double Vol = 0.2;
    double Expiry = 1.0;
    unsigned long Paths = 100000;

    PayoffCall callPayoff(Strike);
    VanillaOption theOption(callPayoff, Expiry);
    ParametersConstant VolParam(Vol);
    ParametersConstant RateParam(r);

    auto PricingEngine = [&](double S) -> double {
        StatisticsMean gatherer;
        RandomMersenne gen(1);
        AntiThetic antiGen(gen);
        SimpleMonteCarlo(theOption, S, VolParam, RateParam, Paths, gatherer, antiGen);
        return gatherer.GetResultsSoFar()[0][0];
    };

    double h = Spot * 0.01;
    double NumericDelta = CalculateDelta(Spot, h, PricingEngine);
    double NumericGamma = CalculateGamma(Spot, h, PricingEngine);

    double ExactDelta = BSDelta(Spot, Strike, r, Vol, Expiry);
    double ExactGamma = BSGamma(Spot, Strike, r, Vol, Expiry);

    fmt::print("\n[Risk Engine Check]\n");
    fmt::print("Numerical Delta: {:.5f} vs Exact: {:.5f}\n", NumericDelta, ExactDelta);
    fmt::print("Numerical Gamma: {:.5f} vs Exact: {:.5f}\n", NumericGamma, ExactGamma);

    EXPECT_NEAR(NumericDelta, ExactDelta, 0.05);
    EXPECT_NEAR(NumericGamma, ExactGamma, 0.005);
}