// src/PathDependentAsian.cpp

#include "../include/PathDependentAsian.h"
#include <numeric>

PathDependentAsian::PathDependentAsian(const MJArray& LookAtTimes,
                                        double DeliveryTime_,
                                        const Payoff& ThePayoff)
    : PathDependent(LookAtTimes), DeliveryTime(DeliveryTime_), PayoffPtr(ThePayoff.clone()) {
}

PathDependentAsian::PathDependentAsian(const PathDependentAsian& original)
    : PathDependent(original),
        DeliveryTime(original.DeliveryTime),
        PayoffPtr(original.PayoffPtr->clone())
{
}

unsigned long PathDependentAsian::PossibleCashFlowTimes() const {
    return 1UL;
}

unsigned long PathDependentAsian::CashFlows(const MJArray& SpotValues,
                                            std::vector<CashFlow>& GeneratedFlows) const {

    double sum = std::accumulate(SpotValues.begin(), SpotValues.end(), 0.0);
    double mean = sum / SpotValues.size();

    GeneratedFlows[0].Amount = (*PayoffPtr)(mean);
    GeneratedFlows[0].TimeIndex = SpotValues.size() - 1;

    return 1UL;
}

std::unique_ptr<PathDependent> PathDependentAsian::clone() const {
    return std::make_unique<PathDependentAsian>(*this);
}