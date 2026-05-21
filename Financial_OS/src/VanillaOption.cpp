// src/VanillaOption.cpp

#include "../include/VanillaOption.h"

VanillaOption::VanillaOption(const Payoff& ThePayoff, double Expiry_)
    : Expiry(Expiry_), PayoffPtr(ThePayoff.clone()) {}

VanillaOption::VanillaOption(const VanillaOption& original)
    : Expiry(original.Expiry), PayoffPtr(original.PayoffPtr->clone()) {}

VanillaOption& VanillaOption::operator=(const VanillaOption& original) {
    if (this != &original) {
        Expiry = original.Expiry;
        PayoffPtr = original.PayoffPtr->clone();
    }
    return *this;
}

double VanillaOption::GetExpiry() const {
    return Expiry;
}

double VanillaOption::OptionPayoff(double Spot) const {
    return (*PayoffPtr)(Spot);
}