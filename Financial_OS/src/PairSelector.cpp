// src/PairSelector.cpp

#include "../include/PairSelector.h"
#include <iostream>
#include <algorithm>
#include <cmath>
#include <limits>

std::vector<PairResult> PairSelector::FindTopPairs(const std::map<std::string, std::vector<double>>& data, int top_n) {
    std::vector<PairResult> all_pairs;

    std::vector<std::string> symbols;
    std::vector<std::vector<double>> returns_cache;

    for (const auto& [symbol, prices] : data) {
        if (prices.size() < 30) continue;
        symbols.push_back(symbol);
        returns_cache.push_back(Analytics::CalculateLogReturns(prices));
    }

    size_t n = symbols.size();
    if (n < 2) return all_pairs;

    for (size_t i = 0; i < n; ++i) {
        for (size_t j = i + 1; j < n; ++j) {
            double corr = Analytics::CalculateCorrelation(returns_cache[i], returns_cache[j]);

            PairResult res;
            res.asset_a = symbols[i];
            res.asset_b = symbols[j];
            res.correlation = corr;
            res.beta = 0.0;
            res.r_squared = 0.0;

            all_pairs.push_back(res);
        }
    }

    std::sort(all_pairs.begin(), all_pairs.end(), [](const PairResult& a, const PairResult& b){
        return std::abs(a.correlation) > std::abs(b.correlation);
    });

    std::vector<PairResult> top_pairs;
    int count = 0;

    for (auto& pair : all_pairs) {
        if (count >= top_n) break;

        const std::vector<double>& prices_a = data.at(pair.asset_a);
        const std::vector<double>& prices_b = data.at(pair.asset_b);

        size_t min_len = std::min(prices_a.size(), prices_b.size());
        std::vector<double> log_a;
        std::vector<double> log_b;
        log_a.reserve(min_len);
        log_b.reserve(min_len);

        auto it_a = prices_a.end() - min_len;
        auto it_b = prices_b.end() - min_len;

        for (; it_a != prices_a.end(); ++it_a, ++it_b) {
            log_a.push_back(std::log(*it_a));
            log_b.push_back(std::log(*it_b));
        }

        LinearRegressionResult reg = Analytics::FitLinearRegression(log_b, log_a);

        pair.beta = reg.beta;
        pair.r_squared = reg.r_squared;

        top_pairs.push_back(pair);
        count++;
    }

    return top_pairs;
}