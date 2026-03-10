#include <gtest/gtest.h>
#include <fmt/core.h>
#include "../include/Bisection.h"
#include "../include/BlackScholesFormulas.h"

class BSCallTwo {
public:
    BSCallTwo(double r_, double d_, double T_, double Spot_, double Strike_)
        : r(r_), d(d_), T(T_), Spot(Spot_), Strike(Strike_) {}

    double operator()(double Vol) const {
        return BlackScholes::CallPrice(Spot, Strike, r, d, Vol, T);
    }

private:
    double r, d, T, Spot, Strike;
};

TEST(SolverTest, ImpliedVolatilityBisection) {
    double Spot = 100.0;
    double Strike = 100.0;
    double r = 0.05;
    double d = 0.0;
    double T = 1.0;

    double TrueVol = 0.2;
    double MarketPrice = BlackScholes::CallPrice(Spot, Strike, r, d, TrueVol, T);

    BSCallTwo theFunction(r, d, T, Spot, Strike);
    double Low = 0.01;
    double High = 1.0;
    double Tolerance = 0.0001;

    double ImpliedVol = Bisection(MarketPrice, Low, High, Tolerance, theFunction);

    fmt::print("\n[Implied Vol Solver]\n");
    fmt::print("Market Price: {:.5f} (from Vol {:.2f})\n", MarketPrice, TrueVol);
    fmt::print("Implied Vol: {:.5f}\n", ImpliedVol);

    EXPECT_NEAR(ImpliedVol, TrueVol, Tolerance);
}