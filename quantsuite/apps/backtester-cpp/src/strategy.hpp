// strategy.hpp
#pragma once
#include <vector>
#include <string>

using namespace std;

enum class StrategyType {
    MA,
    RSI,
    MACD,
    BOLL,
    DONCHIAN,
    BREAKOUT,
};

StrategyType parse_strategy(const string& s);
string strategy_to_string(StrategyType st);

vector<int> ma_cross_signals(const vector<double>& p, int fast, int slow);
vector<double> moving_average_series(const vector<double>& p, int w);
vector<double> equity_curve_long_only(
    const vector<double>& p,
    const vector<double>& ma_fast,
    const vector<double>& ma_slow
);

vector<double> rsi_series(const vector<double>& p, int period);

vector<int> rsi_signals(
    const vector<double>& rsi,
    double buy_level,
    double sell_level
);

vector<double> equity_curve_from_signals(
    const vector<double>& p,
    const vector<int>& sig
);

void macd_series(
    const vector<double>& p,
    int fast,
    int slow,
    int signal_period,
    vector<double>& macd,
    vector<double>& macd_signal,
    vector<double>& macd_hist
);

vector<int> macd_signals(
    const vector<double>& macd,
    const vector<double>& macd_signal
);

vector<double> bollinger_mid(
    const vector<double>& p,
    int window
);

vector<double> bollinger_up(
    const vector<double>& p,
    int window,
    double k
);

vector<double> bollinger_dn(
    const vector<double>& p,
    int window,
    double k
);

vector<int> bollinger_signals(
    const vector<double>& p,
    const vector<double>& mid,
    const vector<double>& up,
    const vector<double>& dn
);

vector<double> donchian_high(const vector<double>& p, int window);
vector<double> donchian_low(const vector<double>& p, int window);

vector<int> donchian_signals(
    const vector<double>& p,
    const vector<double>& high,
    const vector<double>& low
);

vector<int> breakout_signals(
    const vector<double>& p, 
    int window
);