// src/ConvergenceTable.cpp

#include "../include/ConvergenceTable.h"

ConvergenceTable::ConvergenceTable(const StatisticsMC& Inner_)
    : Inner(Inner_.clone()), StoppingPoint(2UL), PathsDone(0) {
}

ConvergenceTable::ConvergenceTable(const ConvergenceTable& original)
    : Inner(original.Inner->clone()),
    ResultsSoFar(original.ResultsSoFar),
    StoppingPoint(original.StoppingPoint),
    PathsDone(original.PathsDone) {
}

ConvergenceTable& ConvergenceTable::operator=(const ConvergenceTable&original) {
    if (this != &original) {
        Inner = original.Inner->clone();
        ResultsSoFar = original.ResultsSoFar;
        StoppingPoint = original.StoppingPoint;
        PathsDone = original.PathsDone;
    }
    return *this;
}

void ConvergenceTable::DumpOneResult(double result) {
    Inner->DumpOneResult(result);
    ++PathsDone;

    if (PathsDone == StoppingPoint) {
        StoppingPoint *= 2;
        std::vector<std::vector<double>> thisResult = Inner->GetResultsSoFar();

        for (auto& row : thisResult) {
            row.push_back(static_cast<double>(PathsDone));
            ResultsSoFar.push_back(row);
        }
    }
}

std::vector<std::vector<double>> ConvergenceTable::GetResultsSoFar() const {
    std::vector<std::vector<double>> tmp(ResultsSoFar);
    
    if (PathsDone * 2 != StoppingPoint) {
        std::vector<std::vector<double>> thisResult = Inner->GetResultsSoFar();
        for (auto& row : thisResult) {
            row.push_back(static_cast<double>(PathsDone));
            tmp.push_back(row);
        }
    }
    return tmp;
}

std::unique_ptr<StatisticsMC> ConvergenceTable::clone() const {
    return std::make_unique<ConvergenceTable>(*this);
}