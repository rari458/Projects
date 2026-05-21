// include/SimpleMC.h

#pragma once
#include "VanillaOption.h"
#include "Parameters.h"
#include "MCStatistics.h"
#include "Random.h"

void SimpleMonteCarlo(const VanillaOption& TheOption,
                        double spot,
                        const Parameters& vol,
                        const Parameters& r,
                        unsigned long numberOfPaths,
                        StatisticsMC& gatherer,
                        RandomBase& generator);