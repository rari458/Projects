// include/PathDependent.h

#pragma once
#include <vector>
#include <memory>

using MJArray = std::vector<double>;

struct CashFlow {
    double Amount;
    unsigned long TimeIndex;
};

class PathDependent {
public:
    PathDependent(const MJArray& LookAtTimes);
    virtual ~PathDependent() = default;

    const MJArray& GetLookAtTimes() const;

    virtual unsigned long PossibleCashFlowTimes() const = 0;
    virtual unsigned long CashFlows(const MJArray& SpotValues,
                                   std::vector<CashFlow>& GeneratedFlows) const = 0;

    virtual std::unique_ptr<PathDependent> clone() const = 0;

private:
    MJArray LookAtTimes;
};