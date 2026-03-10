// include/ExoticBSEngine.h

#pragma once
#include "PathDependent.h"
#include "Parameters.h"
#include "MCStatistics.h"
#include "Random.h"
#include <vector>

class ExoticBSEngine {
public:
    ExoticBSEngine(const PathDependent& TheProduct, 
                    const Parameters& R, 
                    const Parameters& D, 
                    const Parameters& Vol,
                    double Spot);

    void DoSimulation(StatisticsMC& TheGatherer, unsigned long NumberOfPaths, RandomBase& Generator);

private:
    std::unique_ptr<PathDependent> TheProduct;
    Parameters R;
    Parameters D;
    Parameters Vol;
    double Spot;

    MJArray Drifts;
    MJArray StandardDeviations;
    double LogSpot;
    unsigned long NumberOfTimes;
    MJArray Variates;
    MJArray SpotValues;
};