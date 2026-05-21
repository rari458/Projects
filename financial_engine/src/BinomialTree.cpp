// src/BinomialTree.cpp

#include "../include/BinomialTree.h"
#include <cmath>
#include <algorithm>

double SimpleBinomialTree(double Spot,
                        const Parameters& r,
                        const Parameters& d,
                        double Vol,
                        double Expiry,
                        unsigned long Steps,
                        const Payoff& ThePayoff,
                        bool IsAmerican) {

    double dt = Expiry / Steps;
    double sqrt_dt = std::sqrt(dt);

    double u = std::exp(Vol * sqrt_dt);
    double down = 1.0 / u;
    double drift = std::exp((r.Integral(0, dt) - d.Integral(0, dt)));

    double p = (drift - down) / (u - down);
    double one_minus_p = 1.0 - p;

    std::vector<double> TheSpots(Steps + 1);
    std::vector<double> TheValues(Steps + 1);

    for (unsigned long i = 0; i <= Steps; ++i) {
        TheSpots[i] = Spot * std::pow(u, static_cast<double>(i)) * std::pow(down, static_cast<double>(Steps - i));
        TheValues[i] = ThePayoff(TheSpots[i]);
    }

    for (unsigned long i = Steps; i > 0; i--) {
        for (unsigned long j = 0; j < i; j++) {
            double continuationValue = std::exp(-r.Integral(0, dt)) * (p * TheValues[j+1] + one_minus_p * TheValues[j]);

            double currentSpot = Spot * std::pow(u, static_cast<double>(j)) * std::pow(down, static_cast<double>(i - 1 - j));

            if (IsAmerican) {
                double intrinsicValue = ThePayoff(currentSpot);
                TheValues[j] = std::max(intrinsicValue, continuationValue);
            } else {
                TheValues[j] = continuationValue;
            }
        }
    }

    return TheValues[0];
}