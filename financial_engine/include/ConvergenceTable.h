// include/ConvergenceTable.h

#pragma once
#include "MCStatistics.h"
#include <memory>

class ConvergenceTable : public StatisticsMC {
public:
    explicit ConvergenceTable(const StatisticsMC& Inner);
    ConvergenceTable(const ConvergenceTable& original);
    ConvergenceTable& operator=(const ConvergenceTable& original);

    void DumpOneResult(double result) override;
    [[nodiscard]] std::vector<std::vector<double>> GetResultsSoFar() const override;
    [[nodiscard]] std::unique_ptr<StatisticsMC> clone() const override;

private:
    std::unique_ptr<StatisticsMC> Inner;
    std::vector<std::vector<double>> ResultsSoFar;
    unsigned long StoppingPoint;
    unsigned long PathsDone;
};