// strategy.cpp
#include "strategy.hpp"
#include <vector>
#include <cmath>
#include <limits>
#include <algorithm>

using namespace std;

StrategyType parse_strategy(const string& s) {
    if (s == "rsi"  || s == "RSI")  return StrategyType::RSI;
    if (s == "macd" || s == "MACD") return StrategyType::MACD;
    if (s == "boll" || s == "BOLL") return StrategyType::BOLL;
    if (s == "donchian" || s == "DONCHIAN") return StrategyType::DONCHIAN;
    if (s == "breakout" || s == "BREAKOUT") return StrategyType::BREAKOUT;

    return StrategyType::MA;
}

string strategy_to_string(StrategyType st) {
    switch (st) {
    case StrategyType::RSI:      return "rsi";
    case StrategyType::MACD:     return "macd";
    case StrategyType::BOLL:     return "boll";
    case StrategyType::DONCHIAN: return "donchian";
    case StrategyType::BREAKOUT: return "breakout";
    case StrategyType::MA:
    default:
        return "ma";
    }
}

static vector<double> ema_series(const vector<double>& p, int period) {
    const int n = static_cast<int>(p.size());
    vector<double> ema(n, 0.0);
    if (n == 0 || period <= 0) return ema;

    double alpha = 2.0 / (static_cast<double>(period) + 1.0);

    ema[0] = p[0];
    for (int i = 1; i < n; ++i) {
        ema[i] = alpha * p[i] + (1.0 - alpha) * ema[i - 1];
    }
    return ema;
}

vector<double> moving_average_series(const vector<double>& p, int w) {
    const int n = (int)p.size();
    vector<double> ma(n, 0.0);
    if (w <= 0 || n == 0) return ma;
    double sum = 0.0;
    for (int i = 0; i < n; ++i) {
        sum += p[i];
        if (i >= w) sum -= p[i - w];
        if (i >= w - 1) ma[i] = sum / w;
        else ma[i] = 0.0;
    }
    return ma;
}

vector<int> ma_cross_signals(const vector<double>& p, int fast, int slow) {
    auto f = moving_average_series(p, fast);
    auto s = moving_average_series(p, slow);
    const int n = (int)p.size();
    vector<int> sig(n, 0);
    for (int i = 1; i < n; i++) {
        bool prev_le = (i-1 >= 0 ? f[i-1] <= s[i-1] : false);
        bool now_gt  = (f[i] > s[i]);
        bool prev_ge = (i-1 >= 0 ? f[i-1] >= s[i-1] : false);
        bool now_lt  = (f[i] < s[i]);
        if (prev_le && now_gt) sig[i] = +1;
        if (prev_ge && now_lt) sig[i] = -1;
    }
    return sig;
}

vector<double> equity_curve_long_only(
    const vector<double>& p,
    const vector<double>& ma_fast,
    const vector<double>& ma_slow
) {
    const int n = (int)p.size();
    vector<double> eq(n, 1.0);
    if (n == 0) return eq;

    bool long_on = false;
    for (int i = 1; i < n; ++i) {
        if (ma_fast[i] > ma_slow[i]) long_on = true;
        else if (ma_fast[i] < ma_slow[i]) long_on = false;

        double r = (p[i-1] > 0.0) ? (p[i]/p[i-1] - 1.0) : 0.0;
        eq[i] = long_on ? eq[i-1] * (1.0 + r) : eq[i-1];
    }
    return eq;
}

vector<double> rsi_series(const vector<double>& p, int period) {
    const int n = (int)p.size();
    vector<double> rsi(n, 0.0);
    if (n == 0 || period <= 0) return rsi;

    vector<double> gain(n, 0.0), loss(n, 0.0);
    for (int i = 1; i < n; ++i) {
        double diff = p[i] - p[i-1];
        if (diff > 0)      gain[i] = diff;
        else if (diff < 0) loss[i] = -diff;
    }

    int start = min(period, n - 1);
    if (start <= 0) return rsi;

    double avgGain = 0.0, avgLoss = 0.0;
    for (int i = 1; i <= start; ++i) {
        avgGain += gain[i];
        avgLoss += loss[i];
    }
    avgGain /= period;
    avgLoss /= period;

    if (avgLoss == 0.0) {
        rsi[start] = 100.0;
    } else {
        double rs = avgGain / avgLoss;
        rsi[start] = 100.0 - 100.0 / (1.0 + rs);
    }

    for (int i = start + 1; i < n; ++i) {
        avgGain = (avgGain * (period - 1) + gain[i]) / period;
        avgLoss = (avgLoss * (period - 1) + loss[i]) / period;

        if (avgLoss == 0.0) {
            rsi[i] = 100.0;
        } else {
            double rs = avgGain / avgLoss;
            rsi[i] = 100.0 - 100.0 / (1.0 + rs);
        }
    }

    return rsi;
}

vector<int> rsi_signals(
    const vector<double>& rsi,
    double buy_level,
    double sell_level
) {
    const int n = (int)rsi.size();
    vector<int> sig(n, 0);
    if (n == 0) return sig;

    for (int i = 1; i < n; ++i) {
        double prev = rsi[i-1];
        double cur  = rsi[i];

        if (!isfinite(prev) || !isfinite(cur)) continue;

        bool prev_le_buy  = prev <= buy_level;
        bool cur_gt_buy   = cur  > buy_level;
        bool prev_ge_sell = prev >= sell_level;
        bool cur_lt_sell  = cur  < sell_level;

        if (prev_le_buy && cur_gt_buy)   sig[i] = +1;
        if (prev_ge_sell && cur_lt_sell) sig[i] = -1;
    }

    return sig;
}

vector<double> equity_curve_from_signals(
    const vector<double>& p,
    const vector<int>& sig
) {
    const int n = (int)p.size();
    vector<double> eq(n, 1.0);
    if (n == 0) return eq;
    if ((int)sig.size() != n) {
        return eq;
    }

    bool long_on = false;
    for (int i = 1; i < n; ++i) {
        if (sig[i] > 0)      long_on = true;
        else if (sig[i] < 0) long_on = false;

        double r = (p[i-1] > 0.0) ? (p[i] / p[i-1] - 1.0) : 0.0;
        eq[i] = long_on ? eq[i-1] * (1.0 + r) : eq[i-1];
    }

    return eq;
}

void macd_series(
    const vector<double>& p,
    int fast,
    int slow,
    int signal_period,
    vector<double>& macd,
    vector<double>& macd_signal,
    vector<double>& macd_hist
) {
    const int n = static_cast<int>(p.size());
    macd.assign(n, 0.0);
    macd_signal.assign(n, 0.0);
    macd_hist.assign(n, 0.0);
    if (n == 0) return;

    if (fast <= 0) fast = 12;
    if (slow <= 0) slow = 26;
    if (signal_period <= 0) signal_period = 9;

    auto ema_fast = ema_series(p, fast);
    auto ema_slow = ema_series(p, slow);

    for (int i = 0; i < n; ++i) {
        macd[i] = ema_fast[i] - ema_slow[i];
    }

    macd_signal = ema_series(macd, signal_period);

    for (int i = 0; i < n; ++i) {
        macd_hist[i] = macd[i] - macd_signal[i];
    }
}

vector<int> macd_signals(
    const vector<double>& macd,
    const vector<double>& macd_signal
) {
    const int n = static_cast<int>(macd.size());
    vector<int> sig(n, 0);
    if (n == 0 || (int)macd_signal.size() != n) return sig;

    for (int i = 1; i < n; ++i) {
        double prev_diff = macd[i - 1] - macd_signal[i - 1];
        double cur_diff  = macd[i]     - macd_signal[i];

        if (!isfinite(prev_diff) || !isfinite(cur_diff)) continue;

        bool prev_le_0 = (prev_diff <= 0.0);
        bool cur_gt_0  = (cur_diff  > 0.0);
        bool prev_ge_0 = (prev_diff >= 0.0);
        bool cur_lt_0  = (cur_diff  < 0.0);

        if (prev_le_0 && cur_gt_0) sig[i] = +1;
        if (prev_ge_0 && cur_lt_0) sig[i] = -1;
    }

    return sig;
}

vector<double> bollinger_mid(const vector<double>& p, int window) {
    return moving_average_series(p, window);
}

vector<double> bollinger_up(
    const vector<double>& p,
    int window,
    double k
) {
    const int n = (int)p.size();
    vector<double> out(n, 0.0);
    if (n == 0 || window <= 0) return out;

    vector<double> mid = moving_average_series(p, window);
    double sum = 0.0, sumsq = 0.0;

    for (int i = 0; i < n; ++i) {
        sum   += p[i];
        sumsq += p[i] * p[i];

        if (i >= window) {
            sum   -= p[i - window];
            sumsq -= p[i - window] * p[i - window];
        }

        if (i >= window - 1) {
            double mean = mid[i];
            double var  = max(0.0, (sumsq / window) - (mean * mean));
            double sd   = sqrt(var);
            out[i] = mean + k * sd;
        } else {
            out[i] = 0.0;
        }
    }
    return out;
}

vector<double> bollinger_dn(
    const vector<double>& p,
    int window,
    double k
) {
    const int n = (int)p.size();
    vector<double> out(n, 0.0);
    if (n == 0 || window <= 0) return out;

    vector<double> mid = moving_average_series(p, window);
    double sum = 0.0, sumsq = 0.0;

    for (int i = 0; i < n; ++i) {
        sum   += p[i];
        sumsq += p[i] * p[i];

        if (i >= window) {
            sum   -= p[i - window];
            sumsq -= p[i - window] * p[i - window];
        }

        if (i >= window - 1) {
            double mean = mid[i];
            double var  = max(0.0, (sumsq / window) - (mean * mean));
            double sd   = sqrt(var);
            out[i] = mean -k * sd;
        } else {
            out[i] = 0.0;
        }
    }
    return out;
}

vector<int> bollinger_signals(
    const vector<double>& p,
    const vector<double>& mid,
    const vector<double>& up,
    const vector<double>& dn
) {
    const int n = (int)p.size();
    vector<int> sig(n, 0);
    if (n == 0) return sig;
    if ((int)mid.size() != n || (int)up.size() != n || (int)dn.size() != n) {
        return sig;
    }

    for (int i = 1; i < n; ++i) {
        double px = p[i];
        double u  = up[i];
        double d  = dn[i];

        if (!isfinite(px) || !isfinite(u) || !isfinite(d)) {
            continue;
        }

        if (px < d)      sig[i] = +1;
        else if (px > u) sig[i] = -1;
    }

    return sig;
}

vector<double> donchian_high(const vector<double>& p, int window) {
    const int n = (int)p.size();
    vector<double> hi(n, 0.0);
    if (n == 0 || window <= 0) return hi;

    for (int i = 0; i < n; ++i) {
        int start = max(0, i - window + 1);
        double mx = p[start];
        for (int j = start + 1; j <= i; ++j) {
            if (p[j] > mx) mx = p[j];
        }
        hi[i] = mx;
    }
    return hi;
}

vector<double> donchian_low(const vector<double>& p, int window) {
    const int n = (int)p.size();
    vector<double> lo(n, 0.0);
    if (n == 0 || window <= 0) return lo;

    for (int i = 0; i < n; ++i) {
        int start = max(0, i - window + 1);
        double mn = p[start];
        for (int j = start + 1; j <= i; ++j) {
            if (p[j] < mn) mn = p[j];
        }
        lo[i] = mn;
    }
    return lo;
}

vector<int> donchian_signals(
    const vector<double>& p,
    const vector<double>& high,
    const vector<double>& low
) {
    const int n = (int)p.size();
    vector<int> sig(n, 0);
    if (n == 0) return sig;
    if ((int)high.size() != n || (int)low.size() != n) return sig;

    for (int i = 1; i < n; ++i) {
        double prev_p = p[i-1];
        double cur_p  = p[i];
        double prev_hi = high[i-1];
        double prev_lo = low[i-1];

        if (!isfinite(prev_p) || !isfinite(cur_p) ||
            !isfinite(prev_hi) || !isfinite(prev_lo)) {
            continue;
        }

        bool prev_below_hi = prev_p <= prev_hi;
        bool cur_above_hi  = cur_p > prev_hi;
        bool prev_above_lo = prev_p >= prev_lo;
        bool cur_below_lo  = cur_p < prev_lo;

        if (prev_below_hi && cur_above_hi) sig[i] = +1;
        if (prev_above_lo && cur_below_lo) sig[i] = -1;
    }

    return sig;
}

vector<int> breakout_signals(
    const vector<double>& p,
    int window
) {
    const int n = (int)p.size();
    vector<int> sig(n, 0);
    if (n == 0 || window <= 1) return sig;

    for (int i = window; i < n; ++i) {
        double hi = p[i - window];
        double lo = p[i - window];
        for (int j = i - window + 1; j < i; ++j) {
            hi = max(hi, p[j]);
            lo = min(lo, p[j]);
        }

        if (p[i - 1] <= hi && p[i] > hi) {
            sig[i] = +1;
        } else if (p[i - 1] >= lo && p[i] < lo) {
            sig[i] = -1;
        }
    }

    return sig;
}