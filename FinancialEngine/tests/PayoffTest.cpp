#include <gtest/gtest.h>
#include "../include/Payoff.h"

TEST(PayoffTest, CallOptionLogic) {
    double strike = 100.0;
    PayoffCall callOption(strike);

    EXPECT_DOUBLE_EQ(callOption(110.0), 10.0);
    EXPECT_DOUBLE_EQ(callOption(90.0), 0.0);
    EXPECT_DOUBLE_EQ(callOption(100.0), 0.0);
}

TEST(PayoffTest, PutOptionLogic) {
    double strike = 100.0;
    PayoffPut put(strike);

    EXPECT_DOUBLE_EQ(put(90.0), 10.0);
    EXPECT_DOUBLE_EQ(put(100.0), 0.0);
    EXPECT_DOUBLE_EQ(put(110.0), 0.0);
}

TEST(PayoffTest, CloneSemantics) {
    double strike = 100.0;
    PayoffCall original(strike);

    std::unique_ptr<Payoff> copy = original.clone();

    EXPECT_NE(copy.get(), &original);
    EXPECT_DOUBLE_EQ((*copy)(120.0), 20.0);
}