// include/Strategy.h

#ifndef STRATEGY_H
#define STRATEGY_H

#include <string>
#include <vector>
#include <unordered_map>
#include <iostream>
#include <numeric>
#include <cmath>
#include "Analytics.h"
#include "KalmanFilter.h"
#include "BlackScholesFormulas.h"
#include <fmt/core.h>

class Backtester;
class OrderBook;
enum class ActionType { INDEX_REBALANCE, MERGER_ANNOUNCEMENT, EARNINGS_SURPRISE, SHARE_BUYBACK };
enum class CryptoEventType { FUNDING_RATE, MEMPOOL_TRANSACTION, DEX_PRICE_UPDATE };
enum class AltDataType { NLP_SENTIMENT, SATELLITE_IMAGE, CONGRESSIONAL_TRADE };
enum class AnomalyType { SHORT_SQUEEZE, TAIL_RISK, BASIS_TRADE, CROSS_BORDER };
enum class MacroEventType { YIELD_CURVE, CALENDER_SPREAD, FI_CARRY_TRADE, COMMODITY_FX };
enum class AIBhvType { DEEP_ALPHA, GNN_PROPAGATION, CROWDEDNESS, FOMO_PANIC };
enum class FinalTacticsType { QUANTUM_OPT, DIVIDEND_CAPTURE, LITIGATION_ARB, CHAOS_REGIME };
enum class StructArbType {
    VIX_BASIS, DISPERSION, TAX_LOSS, SHARE_CLASS,
    DUAL_LISTED, ETF_ARB, PREDICT_MARKET, ODD_LOT, DELTA_GAMMA
};
enum class DeepCycleType {
    CROSS_ASSET_MOMO, LOW_VOL_ANOMALY, OVERREACTION,
    WINDOW_DRESSING, INVENTORY_CYCLE, LIQUIDATION_HUNT, CROSS_CHAIN_BRIDGE
};
enum class MetaBrainType {
    RISK_PARITY, HMM_REGIME, CLUSTERING,
    ADAPTIVE_ARRIVAL, MULTI_STRAT_MVO, TAIL_RISK  
};

struct CorporateAction {
    ActionType type;
    std::string target_symbol;
    std::string acquiring_symbol;
    double metric;
    double timestamp;
};

struct MicrostructureMessage {
    double timestamp_mu;
    std::string exchange;
    double bid;
    double ask;
    bool is_cancel;
};

struct CryptoEvent {
    CryptoEventType type;
    std::string asset;
    double value;
    double timestamp;
    std::string exchange_a;
    std::string exchange_b;
};

struct AltDataEvent{
    AltDataType type;
    std::string ticker;
    double value;
    double timestamp;
};

struct AnomalyEvent {
    AnomalyType type;
    std::string target;
    std::string hedge_asset;
    double param1;
    double param2;
    double timestamp;
};

struct MacroEvent {
    MacroEventType type;
    std::string asset_a;
    std::string asset_b;
    double rate_a;
    double rate_b;
    double timestamp;
};

struct AIBhvEvent {
    AIBhvType type;
    std::string target_asset;
    std::string related_asset;
    double metric_value;
    double timestamp;
};

struct FinalEvent {
    FinalTacticsType type;
    std::string asset;
    double param1;
    double param2;
    double timestamp;
};

struct L3OrderMessage {
    double timestamp;
    std::string symbol;
    std::string exchange;
    std::string trader_type;
    double price;
    double volume;
    bool is_buy;
};

struct StructuralEvent {
    StructArbType type;
    std::string asset_a;
    std::string asset_b;
    double price_a;
    double price_b;
    double param;
    double timestamp;
};

struct DeepCycleEvent {
    DeepCycleType type;
    std::string asset_main;
    std::string asset_sub;
    double metric;
    double threshold;
    double timestamp;
};

struct MetaEvent {
    MetaBrainType type;
    std::string target;
    double value1;
    double value2;
    double timestamp;
};

class Strategy {
public:
    virtual ~Strategy() = default;
    virtual void on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) = 0;
    virtual void on_order_book_update(class Backtester& engine, const OrderBook& book, double timestamp) {
        (void)engine; (void)book; (void)timestamp;
    }
    virtual void on_corporate_action(Backtester& engine, const CorporateAction& action) {
        (void)engine; (void)action;
    }
    virtual void on_microstructure_msg(Backtester& engine, const MicrostructureMessage& msg) {
        (void)engine; (void)msg;
    }
    virtual void on_crypto_event(Backtester& engine, const CryptoEvent& event) {
        (void)engine; (void)event;
    }
    virtual void on_alt_data(Backtester& engine, const AltDataEvent& event) {
        (void)engine; (void)event;
    }
    virtual void on_anomaly_event(Backtester& engine, const AnomalyEvent& event) {
        (void)engine; (void)event;
    }
    virtual void on_macro_event(Backtester& engine, const MacroEvent& event) {
        (void)engine; (void)event;
    }
    virtual void on_ai_bhv_event(Backtester& engine, const AIBhvEvent& event) {
        (void)engine; (void)event;
    }
    virtual void on_final_event(Backtester& engine, const FinalEvent& event) {
        (void)engine; (void)event;
    }
    virtual void on_l3_message(Backtester& engine, const L3OrderMessage& msg) {
        (void)engine; (void)msg;
    }
    virtual void on_structural_event(Backtester& engine, const StructuralEvent& event) {
        (void)engine; (void)event;
    }
    virtual void on_deep_cycle_event(Backtester& engine, const DeepCycleEvent& event) {
        (void)engine; (void)event;
    }
    virtual void on_meta_event(Backtester& engine, const MetaEvent& event) {
        (void)engine; (void)event;
    }
};

class EMAStrategy : public Strategy {
public:
    EMAStrategy(int short_window = 20, int long_window = 50)
        : short_window_(short_window), long_window_(long_window) {}

    void on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) override;

private:
    int short_window_;
    int long_window_;
    std::unordered_map<std::string, double> current_short_ema_;
    std::unordered_map<std::string, double> current_long_ema_;
    std::unordered_map<std::string, std::vector<double>> history_;
};

class RSIStrategy : public Strategy {
public:
    RSIStrategy(int period = 14, double buy_thresh = 30.0, double sell_thresh = 70.0)
        : period_(period), buy_thresh_(buy_thresh), sell_thresh_(sell_thresh) {}

    void on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) override;

private:
    int period_;
    double buy_thresh_;
    double sell_thresh_;
    std::unordered_map<std::string, std::vector<double>> history_;
};

class MACDStrategy : public Strategy {
public:
    MACDStrategy(int fast = 12, int slow = 26, int signal = 9)
        : fast_period_(fast), slow_period_(slow), signal_period_(signal) {}

    void set_parameters(int fast, int slow, int signal) {
        fast_period_ = fast;
        slow_period_ = slow;
        signal_period_ = signal;
        fast_ema_.clear();
        slow_ema_.clear();
        macd_line_.clear();
        signal_line_.clear();
        history_.clear();
    }

    void on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) override;

private:
    int fast_period_;
    int slow_period_;
    int signal_period_;
    
    std::unordered_map<std::string, double> fast_ema_;
    std::unordered_map<std::string, double> slow_ema_;
    std::unordered_map<std::string, double> macd_line_;
    std::unordered_map<std::string, double> signal_line_;
    std::unordered_map<std::string, std::vector<double>> history_;
};

class BollingerStrategy : public Strategy {
public:
    BollingerStrategy(int period = 20, double std_dev_mult = 2.0)
        : period_(period), mult_(std_dev_mult) {}

    void on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) override;

private:
    int period_;
    double mult_;
    std::unordered_map<std::string, std::vector<double>> history_;
};

class VolatilityStrategy : public Strategy {
public:
    VolatilityStrategy(double k = 0.5) : k_(k) {}

    void on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) override;

    void set_k(double k) { k_ = k; }

private:
    double k_;
};

class OUStrategy : public Strategy {
public:
    OUStrategy(int window = 60, double z_score_thresh = 2.0)
        : window_(window), z_thresh_(z_score_thresh) {}

    void on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) override;

    void set_parameters(int window, double z_thresh) {
        window_ = window;
        z_thresh_ = z_thresh;
        history_.clear();
    }

private:
    int window_;
    double z_thresh_;
    std::unordered_map<std::string, std::vector<double>> history_;
};

class KalmanPairsStrategy : public Strategy {
public:
    KalmanPairsStrategy(const std::string& asset_x = "KO", const std::string& asset_y = "PEP", double z_thresh = 2.0, int window = 30)
        : asset_x_(asset_x), asset_y_(asset_y), z_thresh_(z_thresh), window_(window) {}

    void set_parameters(int window, double z_thresh) {
        window_ = window;
        z_thresh_ = z_thresh;
    }

    void on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) override;

private:
    std::string asset_x_;
    std::string asset_y_;
    double z_thresh_;
    int window_;

    std::unordered_map<double, double> buffer_x_;
    std::unordered_map<double, double> buffer_y_;

    KalmanFilter kf_;
    std::vector<double> spread_history_;
};

class PCAStatArbStrategy : public Strategy {
public:
    PCAStatArbStrategy(int window = 60, double z_thresh = 2.0);

    void on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) override;

private:
    int window_;
    double z_thresh_;
    double last_timestamp_;

    std::map<std::string, std::vector<double>> history_;
    std::map<std::string, double> current_z_scores_;
};

class GammaScalpingStrategy : public Strategy {
public:
    GammaScalpingStrategy(double option_qty = 1000.0, double strike = 100.0, double implied_vol = 0.20, double hedge_band = 5.0);

    void on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) override;

private:
    double option_qty_;
    double strike_;
    double implied_vol_;
    double hedge_band_;
    double risk_free_rate_;
    double time_to_expiry_ = 30.0 / 365.0;
    double initial_option_price_ = 0.0;
    bool is_initialized_ = false;
};

class MarketMakerStrategy : public Strategy {
public:
    MarketMakerStrategy(double risk_aversion = 0.1, double volatility = 0.2, double kappa = 1.5);

    void on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close);
    void on_order_book_update(Backtester& engine, const OrderBook& book, double timestamp) override;

private:
    double gamma_;
    double sigma_;
    double kappa_;
    double time_horizon_;
};

class VWAPExecutionStrategy : public Strategy {
public:
    VWAPExecutionStrategy(double target_qty = 10000.0, double slice_qty = 500.0, double total_time = 200.0);

    void on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) override;
    void on_order_book_update(Backtester& engine, const OrderBook& book, double timestamp) override;

private:
    double target_qty_;
    double slice_qty_;
    double total_time_;
    double executed_qty_;
};

class TWAPExecutionStrategy : public Strategy {
public:
    TWAPExecutionStrategy(double target_qty = 10000.0, double total_time = 200.0);
    void on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) override;
    void on_order_book_update(Backtester& engine, const OrderBook& book, double timestamp) override;

private:
    double target_qty_;
    double total_time_;
    double executed_qty_;
};

class POVExecutionStrategy : public Strategy {
public:
    POVExecutionStrategy(double target_qty = 10000.0, double participation_rate = 0.05);
    void on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) override;
    void on_order_book_update(Backtester& engine, const OrderBook& book, double timestamp) override;

private:
    double target_qty_;
    double participation_rate_;
    double executed_qty_;
    double last_market_volume_;
};

class IcebergExecutionStrategy : public Strategy {
public:
    IcebergExecutionStrategy(double target_qty = 10000.0, double display_size = 100.0);
    void on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) override;
    void on_order_book_update(Backtester& engine, const OrderBook& book, double timestamp) override;

private:
    double target_qty_;
    double display_size_;
    double executed_qty_;
    double current_visible_qty_;
};

class SniperExecutionStrategy : public Strategy {
public:
    SniperExecutionStrategy(double target_qty = 1000.0, double target_price = 99.0);
    void on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) override;
    void on_order_book_update(Backtester& engine, const OrderBook& book, double timestamp) override;

private:
    double target_qty_;
    double target_price_;
    double executed_qty_;
};

class VRPHarvestingStrategy : public Strategy {
public:
    VRPHarvestingStrategy(double strike = 100.0, double time_to_expiry = 30.0 / 252.0, double iv_threshold = 0.05);
    void on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) override;

private:
    double strike_;
    double time_to_expiry_;
    double iv_threshold_;
    double risk_free_rate_ = 0.05;
    bool position_opened_ = false;
    double initial_option_premium_ = 0.0;
    double option_qty_ = 1000.0;
};

class AvellanedaStoikovStrategy : public Strategy {
public:
    AvellanedaStoikovStrategy(double gamma = 0.1, double sigma = 0.2, double kappa = 1.5, double T = 1.0);
    void on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) override;
    void on_order_book_update(Backtester& engine, const OrderBook& book, double timestamp) override;

private:
    double gamma_;
    double sigma_;
    double kappa_;
    double T_;

    double last_bid_quote_ = 0.0;
    double last_ask_quote_ = 0.0;
};

class EventDrivenSuite : public Strategy {
public:
    void on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) override;
    void on_corporate_action(Backtester& engine, const CorporateAction& action) override;

private:
    std::map<std::string, double> latest_prices_;
};

class AdvancedMicrostructureSuite : public Strategy {
public:
    void on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) override;
    void on_microstructure_msg(Backtester& engine, const MicrostructureMessage& msg) override;

private:
    double last_price_A_ = 0.0;
    double last_price_B_ = 0.0;

    int msg_count_ = 0;
    double window_start_ = 0.0;
    bool toxicity_alert_ = false;
};

class CryptoDeFiSuite : public Strategy {
public:
    void on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) override;
    void on_crypto_event(Backtester& engine, const CryptoEvent& event) override;

private:
    std::map<std::string, double> latest_spot_prices_;
};

class AlternativeDataSuite : public Strategy {
public:
    void on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) override;
    void on_alt_data(Backtester& engine, const AltDataEvent& event) override;

private:
    std::map<std::string, double> latest_prices_;
};

class AdvancedDownsideSuite : public Strategy {
public:
    void on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) override;
    void on_anomaly_event(Backtester& engine, const AnomalyEvent& event) override;

private:
    std::map<std::string, double> latest_prices_;
};

class GlobalMacroSuite : public Strategy {
public:
    void on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) override;
    void on_macro_event(Backtester& engine, const MacroEvent& event) override;

private:
    std::map<std::string, double> latest_prices_;
};

class AIBehavioralSuite : public Strategy {
public:
    void on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) override;
    void on_ai_bhv_event(Backtester& engine, const AIBhvEvent& event) override;

private:
    std::map<std::string, double> latest_prices_;
};

class GrandFinaleSuite : public Strategy {
public:
    void on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) override;
    void on_final_event(Backtester& engine, const FinalEvent& event) override;

private:
    std::map<std::string, double> latest_prices_;
};

class L3ExecutionSuite : public Strategy {
public:
    void on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) override;
    void on_order_book_update(Backtester& engine, const OrderBook& book, double timestamp) override;
    void on_l3_message(Backtester& engine, const L3OrderMessage& msg) override;

private:
    double last_trade_price_ = 0.0;
    double vpin_bucket_vol_ = 0.0;
    bool toxicity_shield_active_ = false;
    double arrival_price_ = 0.0;

    std::map<std::string, double> fill_rates_;
};

class StructuralArbSuite : public Strategy {
public:
    void on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) override;
    void on_structural_event(Backtester& engine, const StructuralEvent& event);

private:
    std::map<std::string, double> latest_prices_;
};

class DeepCryptoCycleSuite : public Strategy {
public:
    void on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) override;
    void on_deep_cycle_event(Backtester& engine, const DeepCycleEvent& event);

private:
    std::map<std::string, double> latest_prices_;
};

class MetaBrainSuite : public Strategy {
public:
    void on_market_data(Backtester& engine, const std::string& symbol, double timestamp, double open, double high, double low, double close) override;
    void on_meta_event(Backtester& engine, const MetaEvent& event);

private:
    std::map<std::string, double> latest_prices_;
};

#endif