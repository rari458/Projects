// main.cpp
#include <iostream>
#include <vector>
#include <string>
#include <fstream>
#include <sstream>
#include <limits>
#include <stdexcept>
#include <cmath>

#include "metrics.hpp"
#include "strategy.hpp"

using namespace std;

static bool parse_int(const char* s, int& out) {
    try { out = stoi(string(s)); return true; }
    catch (...) { return false; }
}

static bool parse_double(const char* s, double& out) {
    try { out = stod(string(s)); return true; }
    catch (...) { return false; }
}

static bool load_csv(const string& csv_path,
                    vector<string>& dates,
                    vector<double>& prices)
{
    ifstream fin(csv_path);
    if (!fin) {
        cerr << "Failed to open CSV: " << csv_path << "\n";
        return false;
    }

    dates.clear();
    prices.clear();

    string line;

    if (!fin.eof()) {
        getline(fin, line);
    }

    while (getline(fin, line)) {
        if (line.empty()) continue;
        stringstream ss(line);
        string date, close_str;
        if (!getline(ss, date, ',')) continue;
        if (!getline(ss, close_str, ',')) continue;

        try {
            double c = stod(close_str);
            dates.push_back(date);
            prices.push_back(c);
        } catch (...) {
            continue;
        }
    }
    fin.close();

    if (prices.empty()) {
        cerr << "No valid price rows in CSV: " << csv_path << "\n";
        return false;
    }
    return true;
}

struct StrategyOutput {
    vector<double> equity;
    vector<double> ma_fast;
    vector<double> ma_slow;
    vector<double> rsi;
    vector<double> boll_mid;
    vector<double> boll_up;
    vector<double> boll_dn;
    vector<double> donch_high;
    vector<double> donch_low;

    int buy_cnt = 0;
    int sell_cnt = 0;
};

static StrategyOutput run_strategy_on_prices(
    const vector<double>& prices,
    StrategyType strategy,
    int fast, int slow,
    int rsi_period, double rsi_buy, double rsi_sell)
{
    StrategyOutput out;
    vector<int> sig;

    if (strategy == StrategyType::MA) {
        out.ma_fast = moving_average_series(prices, fast);
        out.ma_slow = moving_average_series(prices, slow);
        sig         = ma_cross_signals(prices, fast, slow);
        out.equity  = equity_curve_long_only(prices, out.ma_fast, out.ma_slow);
    }
    else if (strategy == StrategyType::RSI) {
        out.rsi     = rsi_series(prices, rsi_period);
        sig         = rsi_signals(out.rsi, rsi_buy, rsi_sell);
        out.equity  = equity_curve_from_signals(prices, sig);
    }
    else if (strategy == StrategyType::MACD) {
        vector<double> macd;
        vector<double> macd_signal;
        vector<double> macd_hist;

        macd_series(
            prices,
            fast,
            slow,
            rsi_period,
            macd,
            macd_signal,
            macd_hist
        );

        sig = macd_signals(macd, macd_signal);

        out.equity = equity_curve_from_signals(prices, sig);
    }
    else if (strategy == StrategyType::BOLL) {
        int window = fast;
        double k   = static_cast<double>(slow);

        auto mid = bollinger_mid(prices, window);
        auto up  = bollinger_up(prices, window, k);
        auto dn  = bollinger_dn(prices, window, k);
        
        sig        = bollinger_signals(prices, mid, up, dn);
        out.equity = equity_curve_from_signals(prices, sig);
        out.boll_mid = mid;
        out.boll_up  = up;
        out.boll_dn  = dn;
    }
    else if (strategy == StrategyType::DONCHIAN) {
        int window = fast;
        if (window < 2) window = 20;

        auto hi = donchian_high(prices, window);
        auto lo = donchian_low(prices, window);
        sig     = donchian_signals(prices, hi, lo);

        out.equity     = equity_curve_from_signals(prices, sig);
        out.donch_high = hi;
        out.donch_low  = lo;
    }
    else if (strategy == StrategyType::BREAKOUT) {
        int window = fast;
        if (window < 2) window = 20;
        sig = breakout_signals(prices, window);
        out.equity = equity_curve_from_signals(prices, sig);
    }

    if (out.equity.empty()) {
        out.equity.assign(prices.size(), 1.0);
    }

    out.buy_cnt  = 0;
    out.sell_cnt = 0;
    for (int s : sig) {
        if (s > 0)      ++out.buy_cnt;
        else if (s < 0) ++out.sell_cnt;
    }

    return out;
}

static vector<double> equity_returns(const vector<double>& eq) {
    vector<double> rets;
    if (eq.size() < 2) return rets;
    rets.reserve(eq.size() - 1);
    for (size_t i = 1; i < eq.size(); ++i) {
        if (eq[i - 1] <= 0.0) {
            rets.push_back(0.0);
        } else {
            rets.push_back(eq[i] / eq[i - 1] - 1.0);
        }
    }
    return rets;
}

static double total_return_equity(const vector<double>& eq) {
    if (eq.size() < 2 || eq.front() <= 0.0) return 0.0;
    return eq.back() / eq.front() - 1.0;
}

static double cagr252_equity(const vector<double>& eq) {
    if (eq.size() < 2 || eq.front() <= 0.0 || eq.back() <= 0.0) return 0.0;
    double years = static_cast<double>(eq.size()) / 252.0;
    if (years <= 0.0) return 0.0;
    return pow(eq.back() / eq.front(), 1.0 / years) - 1.0;
}

int main(int argc, char** argv) {
    if(argc < 3) {
        cerr << "Usage:\n";
        cerr << "  backtester <csv_path> <output_json> [strategy] [params...] [--more extra1.csv extra2.csv ...]\n";
        cerr << "Examples:\n";
        cerr << "  backtester data.csv out.json                 (MA, fast=5, slow=20)\n";
        cerr << "  backtester data.csv out.json 5 20            (MA, fast=5, slow=20)\n";
        cerr << "  backtester data.csv out.json ma 10 50        (MA, fast=10, slow=50)\n";
        cerr << "  backtester data.csv.out.json rsi 14 30 70    (RSI, period=14, buy=30, sell=70)\n";
        cerr << "  backtester data.csv.out.json ma 5 20 --more asset2.csv asset3.csv\n";
        return 1;
    }

    string csv_path = argv[1];
    string out_json = argv[2];

    StrategyType strategy = StrategyType::MA;
    string strategy_str   = "ma";

    int fast=5, slow=20;
    int rsi_period = 14;
    double rsi_buy = 30.0, rsi_sell = 70.0;

    int argi = 3;

    if (argc > argi) {
        int tmp = 0;
        if (!parse_int(argv[argi], tmp)) {
            strategy_str = string(argv[argi]);
            strategy = parse_strategy(strategy_str);
            ++argi;
        }
    }

    if (strategy == StrategyType::MA) {
        if (argc > argi) parse_int(argv[argi++], fast);
        if (argc > argi) parse_int(argv[argi++], slow);

        if (fast < 1) fast = 1;
        if (slow < 2) slow = 2;
        if (fast >= slow) {
            fast = slow / 2;
            if (fast < 1) fast = 1;
        }
    } else if (strategy == StrategyType::RSI) {
        if (argc > argi) parse_int(argv[argi++], rsi_period);
        if (argc > argi) parse_double(argv[argi++], rsi_buy);
        if (argc > argi) parse_double(argv[argi++], rsi_sell);

        if (rsi_period < 2) rsi_period = 2;
        if (rsi_buy < 0.0)  rsi_buy  = 0.0;
        if (rsi_buy > 50.0) rsi_buy = 50.0;
        if (rsi_sell < 50.0) rsi_sell = 50.0;
        if (rsi_sell > 100.0) rsi_sell = 100.0;
    } else if (strategy == StrategyType::MACD) {
        if (argc > argi) parse_int(argv[argi++], fast);
        if (argc > argi) parse_int(argv[argi++], slow);
        if (argc > argi) parse_int(argv[argi++], rsi_period);

        if (fast <= 0) fast = 12;
        if (slow <= 0) slow = 26;
        if (rsi_period <= 0) rsi_period = 9;

        if (fast >= slow) {
            fast = slow / 2;
            if (fast < 1) fast = 1;
        }
    } else if (strategy == StrategyType::BOLL) {
        if (argc > argi) parse_int(argv[argi++], fast);
        if (argc > argi) parse_int(argv[argi++], slow);

        if (fast < 2) fast = 20;
        if (slow <= 0) slow = 2;
    } else if (strategy == StrategyType::DONCHIAN) {
        if (argc > argi) parse_int(argv[argi++], fast);
        if (fast < 2) fast = 20;
    } else if (strategy == StrategyType::BREAKOUT) {
        if (argc > argi) parse_int(argv[argi++], fast);
        if (fast < 2) fast = 20;
    }

    string weights_arg;
    vector<string> extra_csvs;
    bool use_risk_parity = false;

    while (argi < argc) {
        string arg = argv[argi];

        if (arg == "--more") {
            ++argi;
            while (argi < argc && 
                string(argv[argi]) != "--weights" &&
                string(argv[argi]) != "--risk-parity") {
                extra_csvs.emplace_back(argv[argi]);
                ++argi;
            }
        }
        else if (arg == "--weights") {
            if (argi + 1 >= argc) {
                cerr << "ERROR: --weights requires a value\n";
                return 1;
            }
            weights_arg = argv[argi + 1];
            argi += 2;
        }
        else if (arg == "--risk-parity") {
            use_risk_parity = true;
            ++argi;
        }
        else {
            cerr << "WARNING: unknown arg: " << arg << "\n";
            ++argi;
        }
    }

    vector<string> base_dates;
    vector<double> base_prices;
    if (!load_csv(csv_path, base_dates, base_prices)) {
        return 1;
    }

    StrategyOutput base_out = run_strategy_on_prices(
        base_prices, strategy,
        fast, slow,
        rsi_period, rsi_buy, rsi_sell
    );

    bool is_portfolio = !extra_csvs.empty();

    vector<vector<double>>  asset_equities;
    vector<string>          asset_files;
    vector<double>          weights;
    vector<double>          portfolio_eq;
    
    if (is_portfolio) {
        asset_equities.push_back(base_out.equity);
        asset_files.push_back(csv_path);

        for (const string& path : extra_csvs) {
            vector<string> d;
            vector<double> p;
            if (!load_csv(path, d, p)) {
                cerr << "Failed to load extra asset CSV: " << path << "\n";
                return 1;
            }

            if (d.size() != base_dates.size()) {
                cerr << "ERROR: date count mismatch between CSV and " << path << "\n";
                return 1;
            }
            for (size_t i = 0; i < d.size(); ++i) {
                if (d[i] != base_dates[i]) {
                    cerr << "ERROR: date mismatch at index " << i
                        <<" between base CSV and " << path << "\n";
                    return 1;
                }
            }

            StrategyOutput out_i = run_strategy_on_prices(
                p, strategy,
                fast, slow,
                rsi_period, rsi_buy, rsi_sell
            );
            asset_equities.push_back(out_i.equity);
            asset_files.push_back(path);
        }

        size_t n_assets = asset_equities.size();
        size_t n_points = base_out.equity.size();

        weights.clear();
        weights.resize(n_assets);

        if (use_risk_parity) {
            vector<double> inv_vol(n_assets, 0.0);
            double sum_inv = 0.0;

            for (size_t a = 0; a < n_assets; ++a) {
                auto rets_a = equity_returns(asset_equities[a]);
                double vol_a = 0.0;
                if (!rets_a.empty()) {
                    vol_a = stdev(rets_a) * sqrt(252.0);
                }
                if (vol_a > 0.0) {
                    inv_vol[a] = 1.0 / vol_a;
                    sum_inv += inv_vol[a];
                } else {
                    inv_vol[a] = 0.0;
                }
            }

            if (sum_inv <= 0.0) {
                double w = 1.0 / static_cast<double>(n_assets);
                for (size_t i = 0; i < n_assets; ++i) {
                    weights[i] = w;
                }
            } else {
                for (size_t i = 0; i < n_assets; ++i) {
                    weights[i] = inv_vol[i] / sum_inv;
                }
            }
        }
        else if (!weights_arg.empty()) {
            vector<double> raw_w;
            string token;
            stringstream ss(weights_arg);

            while (getline(ss, token, ',')) {
                if (token.empty()) continue;
                try {
                    double v = stod(token);
                    raw_w.push_back(v);
                } catch (...) {
                    cerr << "ERROR: invalid weight value: " << token << "\n";
                    return 1;
                }
            }

            if (raw_w.size() != n_assets) {
                cerr << "ERROR: weights count(" << raw_w.size()
                    << ") != n_assets(" << n_assets << ")\n";
                return 1;                
            }

            double sum = 0.0;
            for (double v : raw_w) {
                if (v < 0.0) {
                    cerr << "ERROR: negative weight: " << v << "\n";
                    return 1;
                }
                sum += v;
            }
            if (sum <= 0.0) {
                cerr << "ERROR: sum of weights must be > 0\n";
                return 1;
            }

            for (size_t i = 0; i < n_assets; ++i) {
                weights[i] = raw_w[i] / sum;
            }
        } else {
            double w = 1.0 / static_cast<double>(n_assets);
            for (size_t i = 0; i < n_assets; ++i) {
                weights[i] = w;
            }
        }

        portfolio_eq.assign(n_points, 0.0);
        for (size_t a = 0; a < n_assets; ++a) {
            if (asset_equities[a].size() != n_points) {
                cerr << "ERROR: equity length mismatch for asset index " << a << "\n";
                return 1;
            }
            for (size_t t = 0; t < n_points; ++t) {
                portfolio_eq[t] += weights[a] * asset_equities[a][t];
            }
        }
    } else {
        portfolio_eq = base_out.equity;
        asset_equities.push_back(base_out.equity);
        asset_files.push_back(csv_path);
        weights.push_back(1.0);
    }

    double tr   = total_return_equity(portfolio_eq);
    double cagr = cagr252_equity(portfolio_eq);
    auto   rets = equity_returns(portfolio_eq);
    double vol  = 0.0;
    double shrp = 0.0;

    if (!rets.empty()) {
        vol  = stdev(rets) * sqrt(252.0);
        shrp = sharpe252(rets); 
    }

    vector<double> asset_vols(asset_equities.size(), 0.0);
    vector<double> asset_sharpes(asset_equities.size(), 0.0);

    for (size_t a = 0; a < asset_equities.size(); ++a) {
        auto ra = equity_returns(asset_equities[a]);
        if (!ra.empty()) {
            double v_a = stdev(ra) * sqrt(252.0);
            double s_a = sharpe252(ra);
            asset_vols[a]    = v_a;
            asset_sharpes[a] = s_a;
        }
    }

    int total_buy  = base_out.buy_cnt;
    int total_sell = base_out.sell_cnt;
    if (is_portfolio) {

    }

    double mdd = max_drawdown(portfolio_eq);

    ofstream out(out_json);
    if (!out) {
        cerr << "Failed to open output json: " << out_json << "\n";
        return 1;
    }

    out << "{\n";
    out << "  \"n\": " << portfolio_eq.size() << ",\n";
    out << "  \"total_return\": " << tr << ",\n";
    out << "  \"cagr252\": " << cagr << ",\n";

    if (strategy == StrategyType::MA) {
        out << "  \"fast\": " << fast << ",\n";
        out << "  \"slow\": " << slow << ",\n";
    } else if (strategy == StrategyType::RSI) {
        out << "  \"rsi_period\": " << rsi_period << ",\n";
        out << "  \"rsi_buy\": " << rsi_buy << ",\n";
        out << "  \"rsi_sell\": " << rsi_sell << ",\n";
    } else if (strategy == StrategyType::BOLL) {
        out << "  \"boll_window\": " << fast << ",\n";
        out << "  \"boll_k\": " << slow << ",\n";
    }
    
    out << "  \"strategy\": \"" << strategy_to_string(strategy) << "\",\n";

    out << "  \"signals\": { \"buy\": " << total_buy 
        << ", \"sell\": " << total_sell << " },\n";
    out << "  \"volatility\": " << vol << ",\n";
    out << "  \"max_drawdown\": " << mdd << ",\n";
    out << "  \"sharpe\": " << shrp << ",\n";

    out << "  \"asset_vols\": [";
    for (size_t i = 0; i < asset_vols.size(); ++i) {
        out << asset_vols[i];
        if (i + 1 < asset_sharpes.size()) out << ",";
    }
    out << "],\n";

    out << "  \"asset_sharpes\": [";
    for (size_t i = 0; i < asset_sharpes.size(); ++i) {
        out << asset_sharpes[i];
        if (i + 1 < asset_sharpes.size()) out << ",";
    }
    out << "],\n";

    out << "  \"n_assets\": " << asset_equities.size() << ",\n";
    out << "  \"asset_files\": [";
    for (size_t i = 0; i < asset_files.size(); ++i) {
        out << "\"" << asset_files[i] << "\"";
        if (i + 1 < asset_files.size()) out <<",";
    }
    out << "],\n";

    out << "  \"weights\": [";
    for (size_t i = 0; i < weights.size(); ++i) {
        out << weights[i];
        if (i + 1 < weights.size()) out << ",";
    }
    out << "],\n";

    out << "  \"dates\": [";
    for (size_t i = 0;i < base_dates.size(); ++i) { 
        out << "\"" << base_dates[i] << "\""; 
        if(i + 1 < base_dates.size()) out << ","; 
    }
    out << "],\n";

    out << "  \"close\": [";
    for (size_t i = 0; i < base_prices.size(); ++i) { 
        out << base_prices[i];
        if(i + 1 < base_prices.size()) out << ","; 
    }
    out << "],\n";

    if (strategy == StrategyType::MA) {
        out << "  \"ma_fast\": [";
        for (size_t i = 0; i < base_out.ma_fast.size(); ++i) {
            if ((int)i < fast - 1) out << "null";
            else                   out << base_out.ma_fast[i];
            if (i + 1 < base_out.ma_fast.size()) out << ",";
        }
        out << "],\n";

        out << "  \"ma_slow\": [";
        for (size_t i = 0; i < base_out.ma_slow.size(); ++i) {
            if ((int)i < slow - 1) out << "null";
            else                   out << base_out.ma_slow[i];
            if (i + 1 < base_out.ma_slow.size()) out << ",";
        }
        out << "],\n";
   } else {
        out << "  \"ma_fast\": [";
        for (size_t i = 0; i < base_prices.size(); ++i) {
            out << "null";
            if (i + 1 < base_prices.size()) out << ",";
        }
        out << "],\n";

        out << "  \"ma_slow\": [";
        for (size_t i = 0; i < base_prices.size(); ++i) {
            out << "null";
            if (i + 1 < base_prices.size()) out << ",";
        }
        out << "],\n";
   }

    out << "  \"equity\": [";
    for (size_t i = 0; i < portfolio_eq.size(); ++i) {
        out << portfolio_eq[i];
        if (i + 1 < portfolio_eq.size()) out << ",";
    }
    out << "],\n";

    out << "  \"equity_assets\": [\n";
    for (size_t a = 0; a < asset_equities.size(); ++a) {
        out << "    [";
        const auto& eq = asset_equities[a];
        for (size_t i = 0; i < eq.size(); ++i) {
            out << eq[i];
            if (i + 1 < eq.size()) out << ",";
        }
        out << "]";
        if (a + 1 < asset_equities.size()) out << ",";
        out << "\n";
    }
    out << "  ]";

    if (strategy == StrategyType::RSI) {
        out << ",\n \"rsi\": [";
        for (size_t i = 0; i < base_out.rsi.size(); ++i) {
            if ((int)i < rsi_period) out << "null";
            else                     out << base_out.rsi[i];
            if (i + 1 < base_out.rsi.size()) out << ",";
        }
        out << "]\n";
    } else if(strategy == StrategyType::BOLL) {
        out << ",\n  \"boll_mid\": [";
        for (size_t i = 0; i < base_out.boll_mid.size(); ++i) {
            if ((int)i < fast - 1) out << "null";
            else                   out << base_out.boll_mid[i];
            if (i + 1 < base_out.boll_mid.size()) out << ",";
        }
        out << "],\n  \"boll_up\": [";
        for (size_t i = 0; i < base_out.boll_up.size(); ++i) {
            if ((int)i < fast - 1) out << "null";
            else                   out << base_out.boll_up[i];
            if (i + 1 < base_out.boll_up.size()) out << ",";
        }
        out << "],\n  \"boll_dn\": [";
        for (size_t i = 0; i < base_out.boll_dn.size(); ++i) {
            if ((int)i < fast - 1) out << "null";
            else                   out << base_out.boll_dn[i];
            if (i + 1 < base_out.boll_dn.size()) out << ",";
        }
        out << "]\n";
    } else if (strategy == StrategyType::DONCHIAN) {
        out << ",\n  \"donch_high\": [";
        for (size_t i = 0; i < base_out.donch_high.size(); ++i) {
            if ((int)i < fast - 1) out << "null";
            else                   out << base_out.donch_high[i];
            if (i + 1 < base_out.donch_high.size()) out << ",";
        }
        out << "],\n  \"donch_low\": [";
        for (size_t i = 0; i < base_out.donch_low.size(); ++i) {
            if ((int)i < fast - 1) out << "null";
            else                   out << base_out.donch_low[i];
            if (i + 1 < base_out.donch_low.size()) out << ",";
        }
        out << "]\n";
    } else {
        out << "\n";
    }

    out << "}\n";
    out.close();

    return 0;
}