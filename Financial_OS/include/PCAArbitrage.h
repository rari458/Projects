// include/PCAArbitrage.h

#pragma once

#include <vector>
#include <string>
#include <map>
#include <Eigen/Dense>

struct PCAResult {
    std::map<std::string, double> z_scores;
    std::vector<double> explained_variance;
};

class PCAArbitrage {
public:
    static PCAResult CalculateSignals(const std::map<std::string, std::vector<double>>& prices, int num_components = 1);
};