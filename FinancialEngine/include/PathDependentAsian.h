// include/PathDependentAsian.h

#pragma once
#include "PathDependent.h"
#include "Payoff.h"

class PathDependentAsian : public PathDependent {
public:
    PathDependentAsian(const MJArray& LookAtTimes, 
                        double DeliveryTime, 
                        const Payoff& ThePayoff);

    PathDependentAsian(const PathDependentAsian& original);

    unsigned long PossibleCashFlowTimes() const override;
    unsigned long CashFlows(const MJArray& SpotValues,
                           std::vector<CashFlow>& GeneratedFlows) const override;

    std::unique_ptr<PathDependent> clone() const override;

private:
    double DeliveryTime;
    std::unique_ptr<Payoff> PayoffPtr;
};