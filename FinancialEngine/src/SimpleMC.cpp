// src/SimpleMC.cpp

#include "../include/SimpleMC.h"
#include <cmath>
#include <vector>

void SimpleMonteCarlo(const VanillaOption& TheOption,
                        double spot,
                        const Parameters& vol,
                        const Parameters& r,
                        unsigned long numberOfPaths,
                        StatisticsMC& gatherer,
                        RandomBase& generator) {

    double expiry = TheOption.GetExpiry();
    double variance = vol.IntegralSquare(0, expiry);
    double rootVariance = std::sqrt(variance);
    double itoCorrection = -0.5 * variance;
    double movedSpot = spot * std::exp(r.Integral(0, expiry) + itoCorrection);
    double discounting = std::exp(-r.Integral(0, expiry));

    generator.ResetDimensionality(1);
    generator.Reset();

    std::vector<double> variates(1);

    for (unsigned long i = 0; i < numberOfPaths; ++i) {
        generator.GetGaussians(variates);
        double thisSpot = movedSpot * std::exp(rootVariance * variates[0]);
        double thisPayoff = TheOption.OptionPayoff(thisSpot);

        gatherer.DumpOneResult(thisPayoff * discounting);
    }
}