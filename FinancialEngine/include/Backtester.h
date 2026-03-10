// include/Backtester.h

#ifndef BACKTESTER_H
#define BACKTESTER_H

#include <vector>
#include <string>
#include <memory>
#include <unordered_map>
#include <map>
#include "Strategy.h"
#include "RiskManager.h"
#include "RegimeDetector.h"
#include "OrderBook.h"

struct Trade {
    int id;
    std::string symbol;
    std::string side;
    double quantity;
    double price;
    double commission;
    double timestamp;;
};

class Backtester {
public:
    Backtester(double initial_capital, std::string strategy_type = "EMA", double leverage = 1.0);

    void on_market_data(const std::string& symbol, double timestamp, double open, double high, double low, double close);
    void on_order_book_update(const OrderBook& book, double timestamp);
    void send_order(const std::string& symbol, const std::string& side, double quantity, double price, double timestamp);
    void send_corporate_action(const CorporateAction& action);
    void send_microstructure_msg(const MicrostructureMessage& msg);
    void send_crypto_event(const CryptoEvent& event);
    void send_alt_data(const AltDataEvent& event);
    void send_anomaly_event(const AnomalyEvent& event);
    void send_macro_event(const MacroEvent& event);
    void send_ai_bhv_event(const AIBhvEvent& event);
    void send_final_event(const FinalEvent& event);
    void send_l3_message(const L3OrderMessage& msg);
    void send_structural_event(const StructuralEvent& event);
    void send_deep_cycle_event(const DeepCycleEvent& event);
    void send_meta_event(const MetaEvent& event);
    void set_macd_parameters(int fast, int slow, int signal);
    void set_volatility_k(double k);
    void set_risk_params(double max_drawdown_limit = 0.05, double var_limit = 0.02);
    void set_pairs_parameters(int window, double threshold);
    void set_regime_filter(bool use_filter, int lookback = 252);
    void update_custom_pnl(double pnl) { custom_pnl_ = pnl; }

    double get_total_equity() const;
    double get_cash_balance() const { return capital_; }

    double get_holdings(const std::string& symbol) const;
    double get_leverage() const { return leverage_; }

    std::vector<Trade> get_trade_history() const { return trades_; }
    double get_max_drawdown() const;
    std::vector<double> get_equity_curve() const { return equity_history_; }
    std::vector<double> get_equity_history() const;

    const std::vector<double>& get_opens(const std::string& symbol) const;
    const std::vector<double>& get_highs(const std::string& symbol) const;
    const std::vector<double>& get_lows(const std::string& symbol) const;
    const std::vector<double>& get_closes(const std::string& symbol) const;

private:
    double capital_;
    double leverage_;

    double max_drawdown_limit_ = 0.05;
    double var_limit_ = 0.02;
    double custom_pnl_ = 0.0;
    bool risk_shutdown_ = false;

    bool use_regime_filter_ = false;
    int regime_lookback_ = 252;
    std::map<std::string, std::vector<double>> price_history_buffer_;

    void check_risk_limits(double timestamp);
    void liquidator(double timestamp, const std::string& reason);
    void hibernate_positions(double timestamp, const std::string& symbol, double price);

    std::unordered_map<std::string, double> holdings_;
    std::unordered_map<std::string, double> last_price_;
    std::unordered_map<std::string, double> avg_entry_price_;
    std::unordered_map<std::string, double> highest_price_;

    std::vector<Trade> trades_;

    std::unordered_map<std::string, std::vector<double>> opens_;
    std::unordered_map<std::string, std::vector<double>> highs_;
    std::unordered_map<std::string, std::vector<double>> lows_;
    std::unordered_map<std::string, std::vector<double>> closes_;

    std::vector<double> equity_history_;

    std::unique_ptr<Strategy> strategy_;
    RiskManager risk_manager_{0.05, 0.03};
};

#endif