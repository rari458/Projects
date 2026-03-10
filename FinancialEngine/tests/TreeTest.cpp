#include <gtest/gtest.h>
#include <fmt/core.h>
#include "../include/BinomialTree.h"
#include "../include/Payoff.h"
#include "../include/BlackScholesFormulas.h"
#include "../include/Parameters.h"

TEST(TreeTest, AmericanVsEuropean) {
    double Spot = 100.0;
    double Strike = 100.0;
    double r = 0.05;
    double d = 0.10;
    double Vol = 0.2;
    double Expiry = 1.0;
    unsigned long Steps = 500;

    ParametersConstant rParam(r);
    ParametersConstant dParam(d);
    PayoffPut putPayoff(Strike);
    
    double bsPrice = BlackScholes::PutPrice(Spot, Strike, r, d, Vol, Expiry);
    double euroTreePrice = SimpleBinomialTree(Spot, rParam, dParam, Vol, Expiry, Steps, putPayoff, false);
    double amerTreePrice = SimpleBinomialTree(Spot, rParam, dParam, Vol, Expiry, Steps, putPayoff, true);

    fmt::print("\n[Binomial Tree Check]\n");
    fmt::print("BS European Price:   {:.5f}\n", bsPrice);
    fmt::print("Tree European Price: {:.5f} (Diff: {:.5f})\n", euroTreePrice, std::abs(bsPrice - euroTreePrice));
    fmt::print("Tree American Price: {:.5f}\n", amerTreePrice);

    EXPECT_NEAR(euroTreePrice, bsPrice, 0.1);

    EXPECT_GE(amerTreePrice, euroTreePrice);

    if (amerTreePrice > euroTreePrice + 0.01) {
        fmt::print("-> Early Exercise Premium Detected: {:.5f}\n", amerTreePrice - euroTreePrice);
    }
}