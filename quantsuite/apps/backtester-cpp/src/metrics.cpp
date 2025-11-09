#include "metrics.hpp"
#include <cmath>

using namespace std;

double total_return(const vector<double>& p) {
    if(p.size()<2) return 0.0;
    if(p.front()<=0.0) return 0.0;
    return p.back()/p.front() - 1.0;
}

double cagr252(const vector<double>& p) {
    if(p.size()<2) return 0.0;
    double a=p.front(), b=p.back();
    if(a<=0.0 || b<=0.0) return 0.0;
    double years = static_cast<double>(p.size())/252.0;
    return pow(b/a, 1.0/years) - 1.0;
}