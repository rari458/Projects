// include/RiskManager.h

#ifndef RISKMANAGER_H
#define RISKMANAGER_H

#include <algorithm>
#include <iostream>
#include <fmt/core.h>

class RiskManager {
public:
    RiskManager(double stop_loss_pct = 0.05, double trailing_stop_pct = 0.03)
        : stop_loss_pct_(stop_loss_pct), trailing_stop_pct_(trailing_stop_pct) {}

    bool check_exit_signal(double current_price, double entry_price, double highest_price) {
        if (entry_price <= 0) return false;

        double loss_pct = (current_price - entry_price) / entry_price;
        if (loss_pct < -stop_loss_pct_) {
            fmt::print("      [RISK] STOP LOSS TRIGGERED! ({:.2f}% Loss)\n", loss_pct * 100);
            return true;
        }

        if (current_price > entry_price) {
            double drawdown_from_peak = (current_price - highest_price) / highest_price;
            if (drawdown_from_peak < -trailing_stop_pct_) {
                fmt::print("      [RISK] TRAILING STOP TRIGGERED! (Peak Drop: {:.2f}%)\n", drawdown_from_peak * 100);
                return true;
            }
        }

        return false;
    }

private:
    double stop_loss_pct_;
    double trailing_stop_pct_;
};

#endif