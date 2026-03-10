// include/Analytics.h

#ifndef ANALYTICS_H
#define ANALYTICS_H

#include <vector>
#include <cmath>
#include <algorithm>
#include <numeric>
#include <stdexcept>

struct LinearRegressionResult {
    double alpha;
    double beta;
    double r_squared;
};

class Analytics {
public:
    static std::vector<double> CalculateLogReturns(const std::vector<double>& prices);
    static double CalculateVolatility(const std::vector<double>& returns);
    static double CalculateVaR(const std::vector<double>& returns, double confidence_level);
    static double CalculateParametricVaR(double portfolio_value, double volatility, double confidence_level = 0.95);
    static double CalculateES(const std::vector<double>& returns, double confidence_level);
    static double CalculateRSI(const std::vector<double>& prices, int period = 14);
    static double CalculateMaxDrawdown(const std::vector<double>& equity_curve);
    static double CalculateStdDev(const std::vector<double>& data, int period);
    static double CalculateCorrelation(const std::vector<double>& series_a, const std::vector<double>& series_b);
    static LinearRegressionResult FitLinearRegression(const std::vector<double>& x, const std::vector<double>& y);
};

#endif