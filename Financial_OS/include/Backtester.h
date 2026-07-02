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
#include "EquityCurve.h"
#include "DataHandler.h"
#include "Portfolio.h"

class Backtester {
public:
    Backtester(double initial_capital, std::string strategy_type = "EMA", double leverage = 1.0);

    void on_market_data(const std::string& symbol, double timestamp, double open, double high, double low, double close);
    void on_order_book_update(const OrderBook& book, double timestamp);
    void send_order(const std::string& symbol, const std::string& side, double quantity, double price, double timestamp);
    void send_event(const Event& event);
    void set_macd_parameters(int fast, int slow, int signal);
    void set_volatility_k(double k);
    void set_risk_params(double max_drawdown_limit = 0.05, double var_limit = 0.02);
    void set_pairs_parameters(int window, double threshold);
    void set_regime_filter(bool use_filter, int lookback = 252);
    void update_custom_pnl(double pnl) { portfolio_.set_custom_pnl(pnl); }

    double get_total_equity() const;
    double get_cash_balance() const { return portfolio_.cash(); }

    double get_holdings(const std::string& symbol) const;
    double get_leverage() const { return leverage_; }

    std::vector<Trade> get_trade_history() const { return portfolio_.trades(); }
    double get_max_drawdown() const;
    std::vector<double> get_equity_curve() const { return equity_curve_.history(); }
    std::vector<double> get_equity_history() const;

    const std::vector<double>& get_opens(const std::string& symbol) const;
    const std::vector<double>& get_highs(const std::string& symbol) const;
    const std::vector<double>& get_lows(const std::string& symbol) const;
    const std::vector<double>& get_closes(const std::string& symbol) const;

private:
    Portfolio portfolio_;
    double leverage_;

    double max_drawdown_limit_ = 0.05;
    double var_limit_ = 0.02;
    bool risk_shutdown_ = false;

    bool use_regime_filter_ = false;
    int regime_lookback_ = 252;
    std::map<std::string, std::vector<double>> price_history_buffer_;

    void check_risk_limits(double timestamp);
    void liquidator(double timestamp, const std::string& reason);
    void hibernate_positions(double timestamp, const std::string& symbol, double price);

    DataHandler data_;

    EquityCurve equity_curve_;

    std::unique_ptr<Strategy> strategy_;
    RiskManager risk_manager_{0.05, 0.03};
};

#endif
