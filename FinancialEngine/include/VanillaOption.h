// include/VanillaOption.h

#pragma once
#include <memory>
#include "Payoff.h"

class VanillaOption {
public:
    VanillaOption(const Payoff& ThePayoff, double Expiry);
    VanillaOption(const VanillaOption& original);
    VanillaOption& operator=(const VanillaOption& original);
    ~VanillaOption() = default;

    [[nodiscard]] double GetExpiry() const;
    [[nodiscard]] double OptionPayoff(double Spot) const;

private:
    double Expiry;
    std::unique_ptr<Payoff> PayoffPtr;
};