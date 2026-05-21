// include/BinomialTree.h

#pragma once
#include "Parameters.h"
#include "Payoff.h"
#include <vector>

double SimpleBinomialTree(double Spot, 
                        const Parameters& r, 
                        const Parameters& d, 
                        double Vol, double Expiry, 
                        unsigned long Steps, 
                        const Payoff& ThePayoff, 
                        bool IsAmerican);