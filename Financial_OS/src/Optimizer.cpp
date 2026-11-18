// src/Optimizer.cpp

#include "../include/Optimizer.h"
#include <numeric>
#include <random>
#include "BS_thread_pool.hpp"
#include <thread>
#include <algorithm>
#include <cstdlib>
#include <fstream>
#include <string>
#ifdef __linux__
#include <sched.h>
#endif

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

unsigned int Optimizer::usable_cpus() {
    // A container can use fewer CPUs than the machine has: its affinity mask
    // (--cpuset-cpus) and its CFS quota (--cpus, a k8s limits.cpu) both cap it. A pool
    // sized past that cap only gets throttled: under a 1-CPU quota, 16 threads ran
    // 25% slower than one, with a 2.1x worse p90 (ENGINEERING_DECISIONS #13, #16).
    unsigned int n = std::max(1u, std::thread::hardware_concurrency());
#ifdef __linux__
    cpu_set_t set;
    if (sched_getaffinity(0, sizeof(set), &set) == 0) {
        n = std::min(n, static_cast<unsigned int>(CPU_COUNT(&set)));
    }
    long quota = -1;
    long period = 0;
    std::ifstream v2("/sys/fs/cgroup/cpu.max");  // cgroup v2: "<quota|max> <period>"
    std::string q;
    if (v2 >> q >> period) {
        if (q != "max") quota = std::strtol(q.c_str(), nullptr, 10);
    } else {  // cgroup v1
        std::ifstream qf("/sys/fs/cgroup/cpu/cpu.cfs_quota_us");
        std::ifstream pf("/sys/fs/cgroup/cpu/cpu.cfs_period_us");
        if (!(qf >> quota) || !(pf >> period)) quota = -1;
    }
    if (quota > 0 && period > 0) {
        // Rounded up, as the JVM does: a 1.5-CPU quota gets 2 threads, which can
        // still use all of it, where 1 thread would leave half a CPU idle.
        n = std::min(n, static_cast<unsigned int>((quota + period - 1) / period));
    }
#endif
    return std::max(1u, n);
}

OptimizationResult Optimizer::optimize_sharpe_ratio(int num_simulations, 
    double risk_free_rate, unsigned int num_threads) {
    size_t n_assets = symbols_.size();
    if (n_assets == 0) return {};

    std::vector<double> means(n_assets);
    size_t n_periods = return_matrix_[0].size();
    for (size_t i = 0; i < n_assets; ++i) {
        means[i] = std::accumulate(return_matrix_[i].begin(), return_matrix_[i].end(), 0.0) / n_periods;
    }

    auto cov_matrix = calculate_covariance_matrix();

    std::vector<double> sharpes(num_simulations, -1e9);
    std::vector<double> all_weights(static_cast<size_t>(num_simulations) * n_assets);
    std::vector<double> ann_rets(num_simulations, 0.0);
    std::vector<double> ann_vols(num_simulations, 0.0);

    // One pool, sized once to the CPUs this process may use; num_threads only caps
    // how many of them a call splits its trials across.
    static BS::thread_pool pool(usable_cpus());

    auto run_trial = [&](int sim) {
        thread_local std::mt19937 gen(std::random_device{}());
        std::uniform_real_distribution<> dis(0.0, 1.0);

        thread_local std::vector<double> weights;
        weights.resize(n_assets);

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
            sharpes[sim] = (ann_ret - risk_free_rate) / ann_vol;
            ann_rets[sim] = ann_ret;
            ann_vols[sim] = ann_vol;
            std::copy(weights.begin(), weights.end(), all_weights.begin() + static_cast<size_t>(sim) * n_assets);
        }
    };

    const auto usable = static_cast<unsigned int>(pool.get_thread_count());
    const unsigned int threads = (num_threads == 0) ? usable : std::min(num_threads, usable);
    if (threads == 1) {
        for (int sim = 0; sim < num_simulations; ++sim) run_trial(sim);
    } else {
        pool.submit_loop(0, num_simulations, run_trial, threads).wait();
    }

    auto best_it = std::max_element(sharpes.begin(), sharpes.end());
    size_t best_idx = static_cast<size_t>(std::distance(sharpes.begin(), best_it));

    OptimizationResult best_result;
    best_result.optimal_weights.assign(
        all_weights.begin() + best_idx * n_assets,
        all_weights.begin() + best_idx * n_assets + n_assets
    );
    best_result.portfolio_return = ann_rets[best_idx];
    best_result.portfolio_volatility = ann_vols[best_idx];
    best_result.sharpe_ratio = *best_it;

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

std::vector<std::vector<double>> Optimizer::calculate_shrunk_covariance() const {
    size_t n = return_matrix_.size();
    if (n == 0) return {};
    size_t T = return_matrix_[0].size();
    if (T <= 1) return std::vector<std::vector<double>>(n, std::vector<double>(n, 0.0));

    Eigen::MatrixXd X(n, T);
    for (size_t i = 0; i < n; ++i) {
        double mean = std::accumulate(return_matrix_[i].begin(), return_matrix_[i].end(), 0.0) / T;
        for (size_t t = 0; t < T; ++t) {
            X(i, t) = return_matrix_[i][t] - mean;
        }
    }

    Eigen::MatrixXd S = (X * X.transpose()) / static_cast<double>(T);

    double m  = S.trace() / static_cast<double>(n);
    double d2 = (S - m * Eigen::MatrixXd::Identity(n, n)).squaredNorm() / static_cast<double>(n);

    double b_bar2 = 0.0;
    for (size_t t = 0; t < T; ++t) {
        Eigen::VectorXd xt = X.col(t);
        b_bar2 += (xt * xt.transpose() - S).squaredNorm() / static_cast<double>(n);
    }
    b_bar2 /= static_cast<double>(T) * static_cast<double>(T);

    double b2 = std::min(b_bar2, d2);
    double delta = (d2 > 1e-12) ? b2 / d2 : 0.0;

    Eigen::MatrixXd shrunk = delta * m * Eigen::MatrixXd::Identity(n, n) + (1.0 - delta) * S;

    std::vector<std::vector<double>> out(n, std::vector<double>(n, 0.0));
    for (size_t i = 0; i < n; ++i) {
        for (size_t j = 0; j < n; ++j) {
            out[i][j] = shrunk(i, j);
        }
    }
    return out;
}

OptimizationResult Optimizer::tangency_from_moments(
    const std::vector<double>& means,
    const std::vector<std::vector<double>>& std_cov, double risk_free_rate) const {
    size_t n_assets = means.size();

    Eigen::MatrixXd cov(n_assets, n_assets);
    for (size_t i = 0; i < n_assets; ++i) {
        for (size_t j = 0; j < n_assets; ++j) {
            cov(i, j) = std_cov[i][j] * 252.0;
        }
    }
    cov += Eigen::MatrixXd::Identity(n_assets, n_assets) * 1e-8;

    Eigen::VectorXd excess(n_assets);
    for (size_t i = 0; i < n_assets; ++i) {
        excess(i) = means[i] * 252.0 - risk_free_rate;
    }

    Eigen::VectorXd z = cov.colPivHouseholderQr().solve(excess);
    double z_sum = z.sum();

    std::vector<double> weights(n_assets);
    for (size_t i = 0; i < n_assets; ++i) {
        weights[i] = (std::abs(z_sum) > 1e-12) ? z(i) / z_sum : 1.0 / n_assets;
    }

    auto [p_ret, p_vol] = calculate_portfolio_metrics(weights, means, std_cov);
    double ann_ret = p_ret * 252.0;
    double ann_vol = p_vol * std::sqrt(252.0);
    double sharpe  = (ann_vol > 1e-6) ? (ann_ret - risk_free_rate) / ann_vol : 0.0;

    return {weights, ann_ret, ann_vol, sharpe};
}

OptimizationResult Optimizer::tangency_from_cov(
    const std::vector<std::vector<double>>& std_cov, double risk_free_rate) const {
    size_t n_assets  = symbols_.size();
    size_t n_periods = return_matrix_[0].size();
    std::vector<double> means(n_assets);
    for (size_t i = 0; i < n_assets; ++i) {
        means[i] = std::accumulate(return_matrix_[i].begin(), return_matrix_[i].end(), 0.0) / n_periods;
    }
    return tangency_from_moments(means, std_cov, risk_free_rate);
}

std::vector<double> Optimizer::bayes_stein_means(
    const std::vector<double>& sample_means,
    const std::vector<std::vector<double>>& std_cov, size_t n_periods) const {
    size_t n = sample_means.size();

    Eigen::MatrixXd cov(n, n);
    for (size_t i = 0; i < n; ++i) {
        for (size_t j = 0; j < n; ++j) {
            cov(i, j) = std_cov[i][j];
        }
    }
    cov += Eigen::MatrixXd::Identity(n, n) * 1e-10;

    Eigen::VectorXd mu(n);
    for (size_t i = 0; i < n; ++i) mu(i) = sample_means[i];
    Eigen::VectorXd ones = Eigen::VectorXd::Ones(n);

    Eigen::ColPivHouseholderQR<Eigen::MatrixXd> qr = cov.colPivHouseholderQr();
    Eigen::VectorXd cov_inv_ones = qr.solve(ones);
    double mu0 = ones.dot(qr.solve(mu)) / ones.dot(cov_inv_ones);

    Eigen::VectorXd diff = mu - mu0 * ones;
    double quad = diff.dot(qr.solve(diff));

    double T = static_cast<double>(n_periods);
    double phi = (static_cast<double>(n) + 2.0) / ((static_cast<double>(n) + 2.0) + T * quad);
    if (phi < 0.0) phi = 0.0;
    if (phi > 1.0) phi = 1.0;

    std::vector<double> bs(n);
    for (size_t i = 0; i < n; ++i) {
        bs[i] = (1.0 - phi) * sample_means[i] + phi * mu0;
    }
    return bs;
}

OptimizationResult Optimizer::optimize_max_sharpe_robust(double risk_free_rate) {
    if (symbols_.empty()) return {};
    size_t n_assets  = symbols_.size();
    size_t n_periods = return_matrix_[0].size();

    std::vector<double> sample_means(n_assets);
    for (size_t i = 0; i < n_assets; ++i) {
        sample_means[i] = std::accumulate(return_matrix_[i].begin(), return_matrix_[i].end(), 0.0) / n_periods;
    }

    auto shrunk_cov = calculate_shrunk_covariance();
    auto bs_means   = bayes_stein_means(sample_means, shrunk_cov, n_periods);
    return tangency_from_moments(bs_means, shrunk_cov, risk_free_rate);
}

OptimizationResult Optimizer::optimize_max_sharpe_analytic(double risk_free_rate) {
    if (symbols_.empty()) return {};
    return tangency_from_cov(calculate_covariance_matrix(), risk_free_rate);
}

OptimizationResult Optimizer::optimize_max_sharpe_shrunk(double risk_free_rate) {
    if (symbols_.empty()) return {};
    return tangency_from_cov(calculate_shrunk_covariance(), risk_free_rate);
}