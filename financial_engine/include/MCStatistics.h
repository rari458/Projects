// include/MCStatistics.h

#pragma once
#include <vector>
#include <memory>

class StatisticsMC {
public:
    virtual ~StatisticsMC() = default;
    virtual void DumpOneResult(double result) = 0;
    [[nodiscard]] virtual std::vector<std::vector<double>> GetResultsSoFar() const = 0;
    [[nodiscard]] virtual std::unique_ptr<StatisticsMC> clone() const = 0;
};

class StatisticsMean : public StatisticsMC {
public:
    StatisticsMean();

    void DumpOneResult(double result) override;
    [[nodiscard]] std::vector<std::vector<double>> GetResultsSoFar() const override;
    [[nodiscard]] std::unique_ptr<StatisticsMC> clone() const override;

private:
    double RunningSum;
    unsigned long PathsDone;
};