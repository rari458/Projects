// include/MetaManager.h

#ifndef META_MANAGER_H
#define META_MANAGER_H

#include <vector>
#include <string>
#include <map>
#include "RegimeDetector.h"
#include <fmt/core.h>

class MetaManager {
public:
    MetaManager(double total_capital) : total_capital_(total_capital) {
        strategy_weights_["RiskParity"] = 0.25;
        strategy_weights_["KalmanPairs"] = 0.25;
        strategy_weights_["PCA_Arb"] = 0.25;
        strategy_weights_["VRP_Harvest"] = 0.25;
    }

    void reallocate_capital(const std::string& current_regime) {
        fmt::print("[Meta Brain] Regime Shift Detected: {}. Reallocating Capital...\n", current_regime);

        if (current_regime == "Bull") {
            strategy_weights_["RiskParity"] = 0.50;
            strategy_weights_["KalmanPairs"] = 0.20;
            strategy_weights_["PCA_Arb"] = 0.20;
            strategy_weights_["VRP_Harvest"] = 0.10;
        }
        else if (current_regime == "Bear") {
            strategy_weights_["RiskParity"] = 0.05;
            strategy_weights_["KalmanPairs"] = 0.35;
            strategy_weights_["PCA_Arb"] = 0.35;
            strategy_weights_["VRP_Harvest"] = 0.25;
        }
        else {
            strategy_weights_["RiskParity"] = 0.10;
            strategy_weights_["KalmanPairs"] = 0.30;
            strategy_weights_["PCA_Arb"] = 0.30;
            strategy_weights_["VRP_Harvest"] = 0.30;
        }

        print_current_allocations();
    }

    double get_allocation(const std::string& strategy_name) const {
        if (strategy_weights_.count(strategy_name)) {
            return total_capital_ * strategy_weights_.at(strategy_name);
        }
        return 0.0;
    }

    void print_current_allocations() const {
        fmt::print(" -> Capital Allocations (Total: ${:.0f}):\n", total_capital_);
        for (const auto& [name, weight] : strategy_weights_) {
            fmt::print("    - {:<15} : ${:<10.0f} ({:.0f}%)\n", name, total_capital_ * weight, weight * 100.0);
        }
    }

private:
    double total_capital_;
    std::map<std::string, double> strategy_weights_;
};

#endif