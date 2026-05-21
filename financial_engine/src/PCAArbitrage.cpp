// src/PCAArbitrage.cpp

#include "../include/PCAArbitrage.h"
#include "../include/Analytics.h"
#include <cmath>
#include <numeric>
#include <algorithm>

PCAResult PCAArbitrage::CalculateSignals(const std::map<std::string, std::vector<double>>& prices, int num_components) {
    PCAResult result;
    if (prices.empty()) return result;

    std::vector<std::string> symbols;
    std::vector<std::vector<double>> all_returns;

    for (const auto& [symbol, price_series] : prices) {
        if (price_series.size() < 30) continue;
        symbols.push_back(symbol);
        all_returns.push_back(Analytics::CalculateLogReturns(price_series));
    }

    int N = symbols.size();
    if (N == 0) return result;

    int T = all_returns[0].size();
    for (const auto& ret : all_returns) {
        T = std::min(T, static_cast<int>(ret.size()));
    }

    Eigen::MatrixXd R(T, N);

    for (int j = 0; j < N; ++j) {
        auto r = std::vector<double>(all_returns[j].end() - T, all_returns[j].end());
        double mean = std::accumulate(r.begin(), r.end(), 0.0) / T;
        double sq_sum = std::inner_product(r.begin(), r.end(), r.begin(), 0.0);
        double stdev = std::sqrt((sq_sum / T) - (mean * mean));
        if (stdev < 1e-8) stdev = 1.0;

        for (int i = 0; i < T; ++i) {
            R(i, j) = (r[i] - mean) / stdev;
        }
    }

    Eigen::MatrixXd cov = (R.adjoint() * R) / double(T - 1);
    Eigen::SelfAdjointEigenSolver<Eigen::MatrixXd> solver(cov);

    Eigen::VectorXd eigen_values = solver.eigenvalues().reverse();
    Eigen::MatrixXd eigen_vectors = solver.eigenvectors().rowwise().reverse();

    double total_var = eigen_values.sum();
    int K = std::min(num_components, N);
    for (int i = 0; i < K; ++i) {
        result.explained_variance.push_back(eigen_values(i) / total_var);
    }

    Eigen::MatrixXd V_k = eigen_vectors.leftCols(K);
    Eigen::MatrixXd F = R * V_k;
    Eigen::MatrixXd R_hat = F * V_k.transpose();
    Eigen::MatrixXd E = R - R_hat;

    for (int j = 0; j < N; ++j) {
        Eigen::VectorXd res_col = E.col(j);
        double res_mean = res_col.mean();
        double res_stdev = std::sqrt((res_col.array() - res_mean).square().sum() / (T - 1));

        if (res_stdev < 1e-8) {
            result.z_scores[symbols[j]] = 0.0;
        } else {
            double current_residual = res_col(T - 1);
            result.z_scores[symbols[j]] = -(current_residual - res_mean) / res_stdev;
        }
    }

    return result;
}