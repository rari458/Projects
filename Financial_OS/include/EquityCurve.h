// include/EquityCurve.h

#pragma once
#include <vector>

#include "Analytics.h"

class EquityCurve {
public:
    void record(double equity) { history_.push_back(equity); }

    [[nodiscard]] double max_drawdown() const {
        return Analytics::CalculateMaxDrawdown(history_);
    }

    [[nodiscard]] const std::vector<double>& history() const { return history_; }

private:
    std::vector<double> history_;
};
