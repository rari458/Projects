// metrics.cpp
#include "metrics.hpp"
#include <algorithm>
#include <numeric>
#include <limits>

using namespace std;

double total_return(const vector<double>& p) {
    if (p.size() < 2 || p.front() <= 0) return 0.0;
    return p.back() / p.front() - 1.0;
}

double cagr252(const vector<double>& p) {
    if (p.size() < 2 || p.front() <= 0 || p.back() <= 0) return 0.0;
    const double years = (double)p.size() / 252.0;
    if (years <= 0.0) return 0.0;
    return pow(p.back()/p.front(), 1.0/years) - 1.0;
}

vector<double> daily_returns(const vector<double>& p) {
    vector<double> r;
    if (p.size() < 2) return r;
    r.reserve(p.size()-1);
    for (size_t i = 1; i < p.size(); ++i) {
        if (p[i-1] > 0.0) r.push_back(p[i]/p[i-1] - 1.0);
        else r.push_back(0.0);
    }
    return r;
}

double stdev(const vector<double>& v) {
    if (v.size() < 2) return 0.0;
    double mean = accumulate(v.begin(), v.end(), 0.0) / (double)v.size();
    double acc = 0.0;
    for (double x : v) {
        double d = x - mean;
        acc += d*d;
    }
    return sqrt(acc / (double)(v.size() - 1));
}

double max_drawdown(const vector<double>& equity) {
    double peak = -numeric_limits<double>::infinity();
    double mdd = 0.0;
    for (double x : equity) {
        peak = max(peak, x);
        if (peak > 0.0) mdd = min(mdd, x/peak - 1.0);
    }
    return mdd;
}

double sharpe252(const vector<double>& rets) {
    if (rets.empty()) return 0.0;
    double mean = accumulate(rets.begin(), rets.end(), 0.0) / (double)rets.size();
    double sd = stdev(rets);
    if (sd == 0.0) return 0.0;
    return (mean / sd) * sqrt(252.0);
}