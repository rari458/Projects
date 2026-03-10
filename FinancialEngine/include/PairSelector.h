// include/PairSelector.h

#pragma once
#include <string>
#include <vector>
#include <map>
#include "Analytics.h"

struct PairResult {
    std::string asset_a;
    std::string asset_b;
    double correlation;
    double beta;
    double r_squared;
};

class PairSelector {
public:
    static std::vector<PairResult> FindTopPairs(const std::map<std::string, std::vector<double>>& data, int top_n = 5);
};