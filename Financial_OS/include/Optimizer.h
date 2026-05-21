// include/Optimizer.h

#ifndef OPTIMIZER_H
#define OPTIMIZER_H

#include <vector>
#include <string>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <random>
#include <Eigen/Dense>

struct OptimizationResult {
    std::vector<double> optimal_weights;
    double portfolio_return;
    double portfolio_volatility;
    double sharpe_ratio;
};

class Optimizer {
public:
    void add_asset(const std::string& symbol, const std::vector<double>& returns);
    OptimizationResult optimize_sharpe_ratio(int num_simulations, double risk_free_rate);
    OptimizationResult optimize_inverse_volatility(double risk_free_rate = 0.0);
    OptimizationResult optimize_minimum_variance(double risk_free_rate = 0.0);
    std::vector<std::vector<double>> calculate_covariance_matrix() const;

private:
    std::vector<std::string> symbols_;
    std::vector<std::vector<double>> return_matrix_;

    std::pair<double, double> calculate_portfolio_metrics(
        const std::vector<double>& weights,
        const std::vector<double>& mean_returns,
        const std::vector<std::vector<double>>& cov_matrix) const;
};

#endif