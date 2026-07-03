// include/EquityCurve.h

#pragma once
#include <vector>

#include "Analytics.h"

class EquityCurve {
public:
    // Records one equity point and maintains the running peak + max drawdown
    // incrementally. This mirrors Analytics::CalculateMaxDrawdown EXACTLY (same
    // comparisons, same order, same float ops) but in O(1) per point, so
    // max_drawdown() is O(1) instead of an O(n) rescan. The risk engine calls it
    // every tick, so the old version made the whole run O(n^2).
    void record(double equity) {
        history_.push_back(equity);
        if (history_.size() == 1) {
            peak_ = equity;
            return;
        }
        if (equity > peak_) {
            peak_ = equity;
        } else {
            double drawdown = (equity - peak_) / peak_;
            if (drawdown < max_drawdown_) {
                max_drawdown_ = drawdown;
            }
        }
    }

    [[nodiscard]] double max_drawdown() const { return max_drawdown_; }

    [[nodiscard]] const std::vector<double>& history() const { return history_; }

private:
    std::vector<double> history_;
    double peak_ = 0.0;
    double max_drawdown_ = 0.0;
};
