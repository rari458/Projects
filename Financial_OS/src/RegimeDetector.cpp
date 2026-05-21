// src/RegimeDetector.cpp

#include "../include/RegimeDetector.h"
#include "../include/Analytics.h"
#include <cmath>
#include <algorithm>
#include <limits>
#include <iostream>

struct Point {
    double vol;
    double trend;
    int cluster;
};

RegimeResult RegimeDetector::DetectRegime(const std::vector<double>& prices, int window_size) {
    RegimeResult result = {-1, "Unknown", 0.0, 0.0};
    size_t n = prices.size();
    if (n < static_cast<size_t>(window_size) * 2) return result;

    std::vector<Point> dataset;
    size_t lookback = std::min(n, (size_t)252);

    for (size_t i = n - lookback + static_cast<size_t>(window_size); i < n; ++i) {
        std::vector<double> window(prices.begin() + i - window_size, prices.begin() + i);

        std::vector<double> returns = Analytics::CalculateLogReturns(window);
        double vol = Analytics::CalculateVolatility(returns) * std::sqrt(252);

        double start_p = window.front();
        double end_p = window.back();
        double raw_return = (end_p - start_p) / start_p;
        double trend = raw_return * (252.0 / window_size);

        dataset.push_back({vol, trend, -1});
    }

    if (dataset.empty()) return result;

    Point current_point = dataset.back();
    result.current_volatility = current_point.vol;
    result.current_trend = current_point.trend;

    int K = 3;
    std::vector<Point> centroids(K);

    std::vector<Point> sorted_by_trend = dataset;
    std::sort(sorted_by_trend.begin(), sorted_by_trend.end(), [](const Point& a, const Point& b){
        return a.trend < b.trend;
    });

    if (sorted_by_trend.size() < static_cast<size_t>(K)) return result;

    centroids[0] = sorted_by_trend[0];
    centroids[1] = sorted_by_trend[sorted_by_trend.size() / 2];
    centroids[2] = sorted_by_trend.back();

    for (int iter = 0; iter < 10; ++iter) {
        bool changed = false;
        for (auto& p : dataset) {
            double min_dist = std::numeric_limits<double>::max();
            int best_k = -1;

            for (int k = 0; k < K; ++k) {
                double d_vol = p.vol - centroids[k].vol;
                double d_trend = p.trend - centroids[k].trend;
                double dist = d_vol * d_vol + d_trend * d_trend;

                if (dist < min_dist) {
                    min_dist = dist;
                    best_k = k;
                }
            }
            if (p.cluster != best_k) {
                p.cluster = best_k;
                changed = true;
            }
        }

        if (!changed) break;

        std::vector<double> sum_vol(K, 0.0);
        std::vector<double> sum_trend(K, 0.0);
        std::vector<int> count(K, 0);

        for (const auto& p : dataset) {
            sum_vol[p.cluster] += p.vol;
            sum_trend[p.cluster] += p.trend;
            count[p.cluster]++;
        }

        for (int k = 0; k < K; ++k) {
            if (count[k] > 0) {
                centroids[k].vol = sum_vol[k] / count[k];
                centroids[k].trend = sum_trend[k] / count[k];
            }
        }
    }

    std::vector<std::pair<double, int>> cluster_order;
    for (int k = 0; k < K; ++k) {
        cluster_order.push_back({centroids[k].trend, k});
    }
    std::sort(cluster_order.begin(), cluster_order.end());

    int current_cluster_id = dataset.back().cluster;

    result.state_id = -1;
    for(int i = 0; i < K; ++i) {
        if (cluster_order[i].second == current_cluster_id) {
            result.state_id = i;
            break;
        }
    }

    if (result.state_id == 0) result.state_name = "Bear";
    else if (result.state_id == 1) result.state_name = "Sideways";
    else if (result.state_id == 2) result.state_name = "Bull";

    return result;
}