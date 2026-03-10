// src/Analytics.cpp

#include "../include/Analytics.h"

std::vector<double> Analytics::CalculateLogReturns(const std::vector<double>& prices) {
    if (prices.size() < 2) return {};

    std::vector<double> returns;
    returns.reserve(prices.size() - 1);

    for (size_t i = 1; i < prices.size(); ++i) {
        returns.push_back(std::log(prices[i] / prices[i - 1]));
    }
    return returns;
}

double Analytics::CalculateVolatility(const std::vector<double>& returns) {
    if (returns.empty()) return 0.0;

    double mean = std::accumulate(returns.begin(), returns.end(), 0.0) / returns.size();
    double sq_sum = std::inner_product(returns.begin(), returns.end(), returns.begin(), 0.0);
    double variance = (sq_sum / returns.size()) - (mean * mean);

    return std::sqrt(variance);
}

double Analytics::CalculateVaR(const std::vector<double>& returns, double confidence_level) {
    if (returns.empty()) return 0.0;
    if (confidence_level <= 0.0 || confidence_level >= 1.0)
        throw std::invalid_argument("Confidence level must be between 0 and 1");

    std::vector<double> sorted_returns = returns;
    size_t index = static_cast<size_t>(sorted_returns.size() * (1.0 - confidence_level));
    std::nth_element(sorted_returns.begin(), sorted_returns.begin() + index, sorted_returns.end());

    return -sorted_returns[index];
}

double Analytics::CalculateParametricVaR(double portfolio_value, double volatility, double confidence_level) {
    double z_score = 1.645;
    if (confidence_level >= 0.99) z_score = 2.326;
    else if (confidence_level >= 0.90 && confidence_level < 0.95) z_score = 1.282;

    return portfolio_value * volatility * z_score;
}

double Analytics::CalculateES(const std::vector<double>& returns, double confidence_level) {
    if (returns.empty()) return 0.0;

    std::vector<double> sorted_returns = returns;
    size_t index = static_cast<size_t>(sorted_returns.size() * (1.0 - confidence_level));
    std::nth_element(sorted_returns.begin(), sorted_returns.begin() + index, sorted_returns.end());
    double sum_tail = std::accumulate(sorted_returns.begin(), sorted_returns.begin() + index, 0.0);

    if (index == 0) return 0.0;

    return -(sum_tail / index);
}

double Analytics::CalculateRSI(const std::vector<double>& prices, int period) {
    if (prices.size() <= static_cast<size_t>(period)) return 50.0;

    double gain_sum = 0.0;
    double loss_sum = 0.0;
    
    size_t start_idx = prices.size() - period;

    for (size_t i = start_idx; i < prices.size(); ++i) {
        double change = prices[i] - prices[i - 1];
        if (change > 0) {
            gain_sum += change;
        } else {
            loss_sum += std::abs(change);
        }
    }

    double avg_gain = gain_sum / period;
    double avg_loss = loss_sum / period;

    if (avg_loss == 0) return 100.0;

    double rs = avg_gain / avg_loss;
    return 100.0 - (100.0 / (1.0 + rs));
}

double Analytics::CalculateMaxDrawdown(const std::vector<double>& equity_curve) {
    if (equity_curve.empty()) return 0.0;

    double max_equity = equity_curve[0];
    double max_drawdown = 0.0;

    for (double equity : equity_curve) {
        if (equity > max_equity) {
            max_equity = equity;
        } else {
            double drawdown = (equity - max_equity) / max_equity;
            if (drawdown < max_drawdown) {
                max_drawdown = drawdown;
            }
        }
    }
    return max_drawdown;
}

double Analytics::CalculateStdDev(const std::vector<double>& data, int period) {
    if (data.size() < static_cast<size_t>(period)) return 0.0;

    double sum = 0.0;
    for (int i = 0; i < period; ++i) {
        sum += data[data.size() - 1 - i];
    }
    double mean = sum / period;

    double sq_sum = 0.0;
    for (int i = 0; i < period; ++i) {
        double val = data[data.size() - 1 - i];
        sq_sum += (val - mean) * (val - mean);
    }

    return std::sqrt(sq_sum / period);
}

double Analytics::CalculateCorrelation(const std::vector<double>& series_a, const std::vector<double>& series_b) {
    if (series_a.size() != series_b.size() || series_a.empty()) {
        return 0.0;
    }

    size_t n = series_a.size();

    double sum_a = std::accumulate(series_a.begin(), series_a.end(), 0.0);
    double sum_b = std::accumulate(series_b.begin(), series_b.end(), 0.0);
    double mean_a = sum_a / n;
    double mean_b = sum_b / n;

    double numerator = 0.0;
    double sum_sq_diff_a = 0.0;
    double sum_sq_diff_b = 0.0;

    for (size_t i = 0; i < n; ++i) {
        double diff_a = series_a[i] - mean_a;
        double diff_b = series_b[i] - mean_b;

        numerator += diff_a * diff_b;
        sum_sq_diff_a += diff_a * diff_a;
        sum_sq_diff_b += diff_b * diff_b;
    }

    double denominator = std::sqrt(sum_sq_diff_a) * std::sqrt(sum_sq_diff_b);

    if (denominator == 0.0) return 0.0;

    return numerator / denominator;
}

LinearRegressionResult Analytics::FitLinearRegression(const std::vector<double>& x, const std::vector<double>& y) {
    LinearRegressionResult res = {0.0, 0.0, 0.0};
    if (x.size() != y.size() || x.empty()) return res;

    size_t n = x.size();
    double sum_x = 0.0, sum_y = 0.0, sum_xx = 0.0, sum_xy = 0.0;

    for (size_t i = 0; i < n; ++i) {
        sum_x += x[i];
        sum_y += y[i];
        sum_xx += x[i] * x[i];
        sum_xy += x[i] * y[i];
    }

    double mean_x = sum_x / n;
    double mean_y = sum_y / n;

    double numerator = sum_xy - n * mean_x * mean_y;
    double denominator = sum_xx - n * mean_x * mean_x;

    if (denominator == 0.0) return res;

    res.beta = numerator / denominator;
    res.alpha = mean_y - res.beta * mean_x;

    double ss_tot = 0.0, ss_res = 0.0;
    for (size_t i = 0; i < n; ++i) {
        double y_pred = res.alpha + res.beta * x[i];
        double y_actual = y[i];
        double mean_diff = y_actual - mean_y;

        ss_tot += mean_diff * mean_diff;
        ss_res += (y_actual - y_pred) * (y_actual - y_pred);
    }

    if (ss_tot != 0.0) {
        res.r_squared = 1.0 - (ss_res / ss_tot);
    }

    return res;
}