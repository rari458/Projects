// src/Optimizer.cpp

#include "../include/Optimizer.h"
#include <iostream>
#include <numeric>
#include <random>
#include <fmt/core.h>

void Optimizer::add_asset(const std::string& symbol, const std::vector<double>& returns) {
    symbols_.push_back(symbol);
    return_matrix_.push_back(returns);
}

std::vector<std::vector<double>> Optimizer::calculate_covariance_matrix() const {
    size_t n_assets = return_matrix_.size();
    if (n_assets == 0) return {};
    size_t n_periods = return_matrix_[0].size();

    if (n_periods <= 1) return std::vector<std::vector<double>>(n_assets, std::vector<double>(n_assets, 0.0));

    Eigen::MatrixXd centered_returns(n_assets, n_periods);

    for (size_t i = 0; i < n_assets; ++i) {
        double mean = std::accumulate(return_matrix_[i].begin(), return_matrix_[i].end(), 0.0) / n_periods;
        for (size_t t = 0; t < n_periods; ++t) {
            centered_returns(i, t) = return_matrix_[i][t] - mean;
        }
    }

    Eigen::MatrixXd cov_eigen = (centered_returns * centered_returns.transpose()) / static_cast<double>(n_periods - 1);

    std::vector<std::vector<double>> cov(n_assets, std::vector<double>(n_assets, 0.0));
    for (size_t i = 0; i < n_assets; ++i) {
        for (size_t j = 0; j < n_assets; ++j) {
            cov[i][j] = cov_eigen(i, j);
        }
    }

    return cov;
}

std::pair<double, double> Optimizer::calculate_portfolio_metrics(
    const std::vector<double>& weights,
    const std::vector<double>& mean_returns,
    const std::vector<std::vector<double>>& cov_matrix) const
{
    double port_return = 0.0;
    double port_variance = 0.0;
    size_t n = weights.size();

    for (size_t i = 0; i < n; ++i) {
        port_return += weights[i] * mean_returns[i];
    }

    for (size_t i = 0; i < n; ++i) {
        for (size_t j = 0; j < n; ++j) {
            port_variance += weights[i] * weights[j] * cov_matrix[i][j];
        }
    }

    return {port_return, std::sqrt(port_variance)};
}

OptimizationResult Optimizer::optimize_sharpe_ratio(int num_simulations, double risk_free_rate) {
    size_t n_assets = symbols_.size();
    if (n_assets == 0) return {};

    std::vector<double> means(n_assets);
    size_t n_periods = return_matrix_[0].size();
    for (size_t i = 0; i < n_assets; ++i) {
        means[i] = std::accumulate(return_matrix_[i].begin(), return_matrix_[i].end(), 0.0) / n_periods;
    }

    auto cov_matrix = calculate_covariance_matrix();

    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_real_distribution<> dis(0.0, 1.0);

    double max_sharpe = -1e9;
    OptimizationResult best_result;

    for (int sim = 0; sim < num_simulations; ++sim) {
        std::vector<double> weights(n_assets);
        double sum_weights = 0.0;
        for (size_t i = 0; i < n_assets; ++i) {
            weights[i] = dis(gen);
            sum_weights += weights[i];
        }
        for (size_t i = 0; i < n_assets; ++i) {
            weights[i] /= sum_weights;
        }

        auto [p_ret, p_vol] = calculate_portfolio_metrics(weights, means, cov_matrix);

        double ann_ret = p_ret * 252.0;
        double ann_vol = p_vol * std::sqrt(252.0);

        if (ann_vol > 1e-6) {
            double sharpe = (ann_ret - risk_free_rate) / ann_vol;

            if (sharpe > max_sharpe) {
                max_sharpe = sharpe;
                best_result = {weights, ann_ret, ann_vol, sharpe};
            }
        }
    }

    fmt::print("[Optimizer] Simulation Complete. Tested {} portfolios. Max Sharpe: {:.4f}\n", 
               num_simulations, max_sharpe);

    return best_result;
}

OptimizationResult Optimizer::optimize_inverse_volatility(double risk_free_rate) {
    size_t n_assets = symbols_.size();
    if (n_assets == 0) return {};

    auto cov_matrix = calculate_covariance_matrix();
    std::vector<double> weights(n_assets);
    double sum_inverse_vol = 0.0;

    for (size_t i = 0; i < n_assets; ++i) {
        double vol = std::sqrt(cov_matrix[i][i]);
        if (vol < 1e-8) vol = 1e-8;

        weights[i] = 1.0 / vol;
        sum_inverse_vol += weights[i];
    }

    for (size_t i = 0; i < n_assets; ++i) {
        weights[i] /= sum_inverse_vol;
    }

    size_t n_periods = return_matrix_[0].size();
    std::vector<double> means(n_assets);
    for (size_t i = 0; i < n_assets; ++i) {
        means[i] = std::accumulate(return_matrix_[i].begin(), return_matrix_[i].end(), 0.0) / n_periods;
    }

    auto [p_ret, p_vol] = calculate_portfolio_metrics(weights, means, cov_matrix);
    double ann_ret = p_ret * 252.0;
    double ann_vol = p_vol * std::sqrt(252.0);
    double sharpe = (ann_vol > 1e-6) ? (ann_ret - risk_free_rate) / ann_vol : 0.0;

    return {weights, ann_ret, ann_vol, sharpe};
}

OptimizationResult Optimizer::optimize_minimum_variance(double risk_free_rate) {
    size_t n_assets = symbols_.size();
    if (n_assets == 0) return {};

    auto std_cov = calculate_covariance_matrix();

    Eigen::MatrixXd cov(n_assets, n_assets);
    for(size_t i = 0; i < n_assets; ++i) {
        for(size_t j = 0; j < n_assets; ++j) {
            cov(i, j) = std_cov[i][j];
        }
    }

    cov += Eigen::MatrixXd::Identity(n_assets, n_assets) * 1e-6;

    Eigen::VectorXd ones = Eigen::VectorXd::Ones(n_assets);
    Eigen::VectorXd cov_inv_ones = cov.colPivHouseholderQr().solve(ones);
    double sum_cov_inv_ones = ones.transpose() * cov_inv_ones;

    Eigen::VectorXd optimal_w = cov_inv_ones / sum_cov_inv_ones;

    std::vector<double> weights(n_assets);
    double weight_sum = 0.0;
    for (size_t i = 0; i < n_assets; ++i) {
        weights[i] = std::max(0.0, optimal_w(i));
        weight_sum += weights[i];
    }

    for (size_t i = 0; i < n_assets; ++i) {
        weights[i] = (weight_sum > 0) ? weights[i] / weight_sum : 1.0 / n_assets;
    }

    size_t n_periods = return_matrix_[0].size();
    std::vector<double> means(n_assets);
    for (size_t i = 0; i < n_assets; ++i) {
        means[i] = std::accumulate(return_matrix_[i].begin(), return_matrix_[i].end(), 0.0) / n_periods;
    }

    auto [p_ret, p_vol] = calculate_portfolio_metrics(weights, means, std_cov);
    double ann_ret = p_ret * 252.0;
    double ann_vol = p_vol * std::sqrt(252.0);
    double sharpe = (ann_vol > 1e-6) ? (ann_ret - risk_free_rate) / ann_vol : 0.0;

    return {weights, ann_ret, ann_vol, sharpe};
}