// metrics.hpp
#pragma once
#include <vector>
#include <cmath>

using namespace std;

double total_return(const vector<double>& p);
double cagr252(const vector<double>& prices);

vector<double> daily_returns(const vector<double>& p);
double stdev(const vector<double>& v);
double max_drawdown(const vector<double>& equity);
double sharpe252(const vector<double>& rets);