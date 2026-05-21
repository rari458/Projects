// src/ExoticBSEngine.cpp

#include "../include/ExoticBSEngine.h"
#include <cmath>

ExoticBSEngine::ExoticBSEngine(const PathDependent& TheProduct_, 
                                const Parameters& R_, 
                                const Parameters& D_, 
                                const Parameters& Vol_, 
                                double Spot_)
    : TheProduct(TheProduct_.clone()), R(R_), D(D_), Vol(Vol_), Spot(Spot_)
{
    const MJArray& Times = TheProduct->GetLookAtTimes();
    NumberOfTimes = Times.size();

    Drifts.resize(NumberOfTimes);
    StandardDeviations.resize(NumberOfTimes);

    double Variance = Vol.IntegralSquare(0, Times[0]);
    Drifts[0] = R.Integral(0, Times[0]) - D.Integral(0, Times[0]) - 0.5 * Variance;
    StandardDeviations[0] = std::sqrt(Variance);

    for (unsigned long j = 1; j < NumberOfTimes; ++j) {
        double thisVariance = Vol.IntegralSquare(Times[j-1], Times[j]);
        Drifts[j] = R.Integral(Times[j-1], Times[j]) - D.Integral(Times[j-1], Times[j]) - 0.5 * thisVariance;
        StandardDeviations[j] = std::sqrt(thisVariance);
    }

    LogSpot = std::log(Spot);
    Variates.resize(NumberOfTimes);
    SpotValues.resize(NumberOfTimes);
}

void ExoticBSEngine::DoSimulation(StatisticsMC& TheGatherer, unsigned long NumberofPaths, RandomBase& Generator) {
    Generator.ResetDimensionality(NumberOfTimes);
    Generator.Reset();

    std::vector<CashFlow> TheseCashFlows(TheProduct->PossibleCashFlowTimes());
    const MJArray& Times = TheProduct->GetLookAtTimes();

    for (unsigned long i = 0; i < NumberofPaths; ++i) {
        Generator.GetGaussians(Variates);

        double CurrentLogSpot = LogSpot;

        for (unsigned long j = 0; j < NumberOfTimes; ++j) {
            CurrentLogSpot += Drifts[j];
            CurrentLogSpot += StandardDeviations[j] * Variates[j];
            SpotValues[j] = std::exp(CurrentLogSpot);
        }

        unsigned long NumberFlows = TheProduct->CashFlows(SpotValues, TheseCashFlows);
        double Value = 0.0;

        for (unsigned long j = 0; j < NumberFlows; ++j) {
            double FlowTime = Times[TheseCashFlows[j].TimeIndex];
            Value += TheseCashFlows[j].Amount * std::exp(-R.Integral(0, FlowTime));
        }

        TheGatherer.DumpOneResult(Value);
    }
}