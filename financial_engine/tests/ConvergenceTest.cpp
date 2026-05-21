#include <gtest/gtest.h>
#include <fmt/core.h>
#include "../include/SimpleMC.h"
#include "../include/VanillaOption.h"
#include "../include/MCStatistics.h"
#include "../include/ConvergenceTable.h"
#include "../include/Random.h"

TEST(MonteCarloTest, ConvergenceLogging) {
    double spot = 100.0;
    double strike = 100.0;
    double expiry = 1.0;
    double vol = 0.2;
    double r = 0.05;
    unsigned long paths = 8192;

    PayoffCall callPayoff(strike);
    VanillaOption theOption(callPayoff, expiry);

    StatisticsMean meanGatherer;
    ConvergenceTable table(meanGatherer);

    RandomMersenne generator(1);

    SimpleMonteCarlo(theOption, spot, vol, r, paths, table, generator);

    auto results = table.GetResultsSoFar();

    EXPECT_GT(results.size(), 10);

    fmt::print("\n[Convergence Table]\n");
    fmt::print("{:<10} | {:<15}\n", "Paths", "Price");
    fmt::print("{:-<27}\n", "");

    for (const auto& row : results) {
        double price = row[0];
        double pathsDone = row[1];
        fmt::print("{:<10.0f} | {:.5f}\n", pathsDone, price);

        EXPECT_GT(price, 0.0);
    }
}