// src/MCStatistics.cpp

#include "../include/MCStatistics.h"

StatisticsMean::StatisticsMean() : RunningSum(0.0), PathsDone(0UL) {}

void StatisticsMean::DumpOneResult(double result) {
    PathsDone++;
    RunningSum += result;
}

std::vector<std::vector<double>> StatisticsMean::GetResultsSoFar() const {
    std::vector<std::vector<double>> Results(1);
    Results[0].resize(1);

    if (PathsDone > 0) {
        Results[0][0] = RunningSum / static_cast<double>(PathsDone);
    } else {
        Results[0][0] = 0.0;
    }

    return Results;
}

std::unique_ptr<StatisticsMC> StatisticsMean::clone() const {
    return std::make_unique<StatisticsMean>(*this);
}