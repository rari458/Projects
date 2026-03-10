#include <gtest/gtest.h>
#include <fmt/core.h>
#include "../include/PayoffFactory.h"
#include "../include/Payoff.h"

TEST(FactoryTest, CreateFromStrings) {
    double strike = 100.0;

    std::unique_ptr<Payoff> call = PayoffFactory::Instance().CreatePayoff("call", strike);
    ASSERT_NE(call, nullptr);
    EXPECT_DOUBLE_EQ((*call)(120.0), 20.0);

    std::unique_ptr<Payoff> put = PayoffFactory::Instance().CreatePayoff("put", strike);
    ASSERT_NE(put, nullptr);
    EXPECT_DOUBLE_EQ((*put)(80.0), 20.0);

    std::unique_ptr<Payoff> unknown = PayoffFactory::Instance().CreatePayoff("digital", strike);
    EXPECT_EQ(unknown, nullptr);
}