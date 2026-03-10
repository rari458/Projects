// src/Payoff.cpp

#include "../include/Payoff.h"
#include <algorithm>

PayoffCall::PayoffCall(double strike) : strike_(strike) {}

double PayoffCall::operator()(double spot) const {
    return std::max(spot - strike_, 0.0);
}

std::unique_ptr<Payoff> PayoffCall::clone() const {
    return std::make_unique<PayoffCall>(*this);
}

PayoffPut::PayoffPut(double strike) : strike_(strike) {}

double PayoffPut::operator()(double spot) const {
    return std::max(strike_ - spot, 0.0);
}

std::unique_ptr<Payoff> PayoffPut::clone() const {
    return std::make_unique<PayoffPut>(*this);
}