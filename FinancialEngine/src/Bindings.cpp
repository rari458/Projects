// src/Bindings.cpp

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "../include/BlackScholesFormulas.h"
#include "../include/BinomialTree.h"
#include "../include/PayoffFactory.h"
#include "../include/Payoff.h"
#include "../include/Parameters.h"
#include "../include/Analytics.h"
#include "../include/Backtester.h"
#include "../include/Optimizer.h"
#include "../include/HyperOptimizer.h"
#include "../include/PairSelector.h"
#include "../include/RegimeDetector.h"
#include "../include/PCAArbitrage.h"
#include "../include/OrderBook.h"
#include "../include/Strategy.h"

namespace py = pybind11;

double RunBinomialTree(double Spot, double Rate, double Div, double Vol, double Expiry, int Steps, std::string PayoffType, double Strike, bool IsAmerican) {
    auto PayoffPtr = PayoffFactory::Instance().CreatePayoff(PayoffType, Strike);
    if (!PayoffPtr) {
        throw std::runtime_error("Unknown Payoff ID");
    }
    ParametersConstant r(Rate);
    ParametersConstant d(Div);
    return SimpleBinomialTree(Spot, r, d, Vol, Expiry, Steps, *PayoffPtr, IsAmerican);
}

PYBIND11_MODULE(FinancialEngine, m) {
    m.doc() = "Financial Engine powered by C++ Core (Multi-Asset & Kalman)";

    // =========================================================================
    // 1. Core Financial Math & Pricing Engines
    // =========================================================================
    m.def("black_scholes_call", &BlackScholes::CallPrice, "Calculate Call Price",
          py::arg("spot"), py::arg("strike"), py::arg("r"), py::arg("d"), py::arg("vol"), py::arg("expiry"));
          
    m.def("black_scholes_put", &BlackScholes::PutPrice, "Calculate European Put Price",
          py::arg("spot"), py::arg("strike"), py::arg("r"), py::arg("d"), py::arg("vol"), py::arg("expiry"));

    m.def("calculate_greeks", &BlackScholes::CalculateGreeks, "Calculate Options Greeks",
          py::arg("spot"), py::arg("strike"), py::arg("r"), py::arg("d"), py::arg("vol"), py::arg("expiry"), py::arg("is_call"));

    m.def("binomial_tree_price", &RunBinomialTree, "Binomial Tree Option Pricing",
        py::arg("spot"), py::arg("rate"), py::arg("div"), py::arg("vol"), py::arg("expiry"),
        py::arg("steps"), py::arg("payoff_type"), py::arg("strike"), py::arg("is_american"));

    // =========================================================================
    // 2. Enums & Event Structures (The 75-Strategy Communication Protocol)
    // =========================================================================

    // Enums
    py::enum_<ActionType>(m, "ActionType")
        .value("INDEX_REBALANCE", ActionType::INDEX_REBALANCE)
        .value("MERGER_ANNOUNCEMENT", ActionType::MERGER_ANNOUNCEMENT)
        .value("EARNINGS_SURPRISE", ActionType::EARNINGS_SURPRISE)
        .value("SHARE_BUYBACK", ActionType::SHARE_BUYBACK).export_values();

    py::enum_<CryptoEventType>(m, "CryptoEventType")
        .value("FUNDING_RATE", CryptoEventType::FUNDING_RATE)
        .value("MEMPOOL_TRANSACTION", CryptoEventType::MEMPOOL_TRANSACTION)
        .value("DEX_PRICE_UPDATE", CryptoEventType::DEX_PRICE_UPDATE).export_values();

    py::enum_<AltDataType>(m, "AltDataType")
        .value("NLP_SENTIMENT", AltDataType::NLP_SENTIMENT)
        .value("SATELLITE_IMAGE", AltDataType::SATELLITE_IMAGE)
        .value("CONGRESSIONAL_TRADE", AltDataType::CONGRESSIONAL_TRADE).export_values();

    py::enum_<AnomalyType>(m, "AnomalyType")
        .value("SHORT_SQUEEZE", AnomalyType::SHORT_SQUEEZE)
        .value("TAIL_RISK", AnomalyType::TAIL_RISK)
        .value("BASIS_TRADE", AnomalyType::BASIS_TRADE)
        .value("CROSS_BORDER", AnomalyType::CROSS_BORDER).export_values();

    py::enum_<MacroEventType>(m, "MacroEventType")
        .value("YIELD_CURVE", MacroEventType::YIELD_CURVE)
        .value("CALENDAR_SPREAD", MacroEventType::CALENDER_SPREAD)
        .value("FI_CARRY_TRADE", MacroEventType::FI_CARRY_TRADE)
        .value("COMMODITY_FX", MacroEventType::COMMODITY_FX).export_values();

    py::enum_<AIBhvType>(m, "AIBhvType")
        .value("DEEP_ALPHA", AIBhvType::DEEP_ALPHA)
        .value("GNN_PROPAGATION", AIBhvType::GNN_PROPAGATION)
        .value("CROWDEDNESS", AIBhvType::CROWDEDNESS)
        .value("FOMO_PANIC", AIBhvType::FOMO_PANIC).export_values();

    py::enum_<FinalTacticsType>(m, "FinalTacticsType")
        .value("QUANTUM_OPT", FinalTacticsType::QUANTUM_OPT)
        .value("DIVIDEND_CAPTURE", FinalTacticsType::DIVIDEND_CAPTURE)
        .value("LITIGATION_ARB", FinalTacticsType::LITIGATION_ARB)
        .value("CHAOS_REGIME", FinalTacticsType::CHAOS_REGIME).export_values();

    py::enum_<StructArbType>(m, "StructArbType")
        .value("VIX_BASIS", StructArbType::VIX_BASIS)
        .value("DISPERSION", StructArbType::DISPERSION)
        .value("TAX_LOSS", StructArbType::TAX_LOSS)
        .value("SHARE_CLASS", StructArbType::SHARE_CLASS)
        .value("DUAL_LISTED", StructArbType::DUAL_LISTED)
        .value("ETF_ARB", StructArbType::ETF_ARB)
        .value("PREDICT_MARKET", StructArbType::PREDICT_MARKET)
        .value("ODD_LOT", StructArbType::ODD_LOT)
        .value("DELTA_GAMMA", StructArbType::DELTA_GAMMA).export_values();

    py::enum_<DeepCycleType>(m, "DeepCycleType")
        .value("CROSS_ASSET_MOMO", DeepCycleType::CROSS_ASSET_MOMO)
        .value("LOW_VOL_ANOMALY", DeepCycleType::LOW_VOL_ANOMALY)
        .value("OVERREACTION", DeepCycleType::OVERREACTION)
        .value("WINDOW_DRESSING", DeepCycleType::WINDOW_DRESSING)
        .value("INVENTORY_CYCLE", DeepCycleType::INVENTORY_CYCLE)
        .value("LIQUIDATION_HUNT", DeepCycleType::LIQUIDATION_HUNT)
        .value("CROSS_CHAIN_BRIDGE", DeepCycleType::CROSS_CHAIN_BRIDGE).export_values();

    py::enum_<MetaBrainType>(m, "MetaBrainType")
        .value("RISK_PARITY", MetaBrainType::RISK_PARITY)
        .value("HMM_REGIME", MetaBrainType::HMM_REGIME)
        .value("CLUSTERING", MetaBrainType::CLUSTERING)
        .value("ADAPTIVE_ARRIVAL", MetaBrainType::ADAPTIVE_ARRIVAL)
        .value("MULTI_STRAT_MVO", MetaBrainType::MULTI_STRAT_MVO)
        .value("TAIL_RISK", MetaBrainType::TAIL_RISK).export_values();

    // Structs
    py::class_<CorporateAction>(m, "CorporateAction")
        .def(py::init<ActionType, std::string, std::string, double, double>())
        .def_readwrite("type", &CorporateAction::type)
        .def_readwrite("target_symbol", &CorporateAction::target_symbol)
        .def_readwrite("acquiring_symbol", &CorporateAction::acquiring_symbol)
        .def_readwrite("metric", &CorporateAction::metric)
        .def_readwrite("timestamp", &CorporateAction::timestamp);

    py::class_<MicrostructureMessage>(m, "MicrostructureMessage")
        .def(py::init<double, std::string, double, double, bool>())
        .def_readwrite("timestamp_mu", &MicrostructureMessage::timestamp_mu)
        .def_readwrite("exchange", &MicrostructureMessage::exchange)
        .def_readwrite("bid", &MicrostructureMessage::bid)
        .def_readwrite("ask", &MicrostructureMessage::ask)
        .def_readwrite("is_cancel", &MicrostructureMessage::is_cancel);

    py::class_<CryptoEvent>(m, "CryptoEvent")
        .def(py::init<CryptoEventType, std::string, double, double, std::string, std::string>())
        .def_readwrite("type", &CryptoEvent::type)
        .def_readwrite("asset", &CryptoEvent::asset)
        .def_readwrite("value", &CryptoEvent::value)
        .def_readwrite("timestamp", &CryptoEvent::timestamp)
        .def_readwrite("exchange_a", &CryptoEvent::exchange_a)
        .def_readwrite("exchange_b", &CryptoEvent::exchange_b);

    py::class_<AltDataEvent>(m, "AltDataEvent")
        .def(py::init<AltDataType, std::string, double, double>())
        .def_readwrite("type", &AltDataEvent::type)
        .def_readwrite("ticker", &AltDataEvent::ticker)
        .def_readwrite("value", &AltDataEvent::value)
        .def_readwrite("timestamp", &AltDataEvent::timestamp);

    py::class_<AnomalyEvent>(m, "AnomalyEvent")
        .def(py::init<AnomalyType, std::string, std::string, double, double, double>())
        .def_readwrite("type", &AnomalyEvent::type)
        .def_readwrite("target", &AnomalyEvent::target)
        .def_readwrite("hedge_asset", &AnomalyEvent::hedge_asset)
        .def_readwrite("param1", &AnomalyEvent::param1)
        .def_readwrite("param2", &AnomalyEvent::param2)
        .def_readwrite("timestamp", &AnomalyEvent::timestamp);

    py::class_<MacroEvent>(m, "MacroEvent")
        .def(py::init<MacroEventType, std::string, std::string, double, double, double>())
        .def_readwrite("type", &MacroEvent::type)
        .def_readwrite("asset_a", &MacroEvent::asset_a)
        .def_readwrite("asset_b", &MacroEvent::asset_b)
        .def_readwrite("rate_a", &MacroEvent::rate_a)
        .def_readwrite("rate_b", &MacroEvent::rate_b)
        .def_readwrite("timestamp", &MacroEvent::timestamp);

    py::class_<AIBhvEvent>(m, "AIBhvEvent")
        .def(py::init<AIBhvType, std::string, std::string, double, double>())
        .def_readwrite("type", &AIBhvEvent::type)
        .def_readwrite("target_asset", &AIBhvEvent::target_asset)
        .def_readwrite("related_asset", &AIBhvEvent::related_asset)
        .def_readwrite("metric_value", &AIBhvEvent::metric_value)
        .def_readwrite("timestamp", &AIBhvEvent::timestamp);

    py::class_<FinalEvent>(m, "FinalEvent")
        .def(py::init<FinalTacticsType, std::string, double, double, double>())
        .def_readwrite("type", &FinalEvent::type)
        .def_readwrite("asset", &FinalEvent::asset)
        .def_readwrite("param1", &FinalEvent::param1)
        .def_readwrite("param2", &FinalEvent::param2)
        .def_readwrite("timestamp", &FinalEvent::timestamp);

    py::class_<L3OrderMessage>(m, "L3OrderMessage")
        .def(py::init<double, std::string, std::string, std::string, double, double, bool>())
        .def_readwrite("timestamp", &L3OrderMessage::timestamp)
        .def_readwrite("symbol", &L3OrderMessage::symbol)
        .def_readwrite("exchange", &L3OrderMessage::exchange)
        .def_readwrite("trader_type", &L3OrderMessage::trader_type)
        .def_readwrite("price", &L3OrderMessage::price)
        .def_readwrite("volume", &L3OrderMessage::volume)
        .def_readwrite("is_buy", &L3OrderMessage::is_buy);

    py::class_<StructuralEvent>(m, "StructuralEvent")
        .def(py::init<StructArbType, std::string, std::string, double, double, double, double>())
        .def_readwrite("type", &StructuralEvent::type)
        .def_readwrite("asset_a", &StructuralEvent::asset_a)
        .def_readwrite("asset_b", &StructuralEvent::asset_b)
        .def_readwrite("price_a", &StructuralEvent::price_a)
        .def_readwrite("price_b", &StructuralEvent::price_b)
        .def_readwrite("param", &StructuralEvent::param)
        .def_readwrite("timestamp", &StructuralEvent::timestamp);

    py::class_<DeepCycleEvent>(m, "DeepCycleEvent")
        .def(py::init<DeepCycleType, std::string, std::string, double, double, double>())
        .def_readwrite("type", &DeepCycleEvent::type)
        .def_readwrite("asset_main", &DeepCycleEvent::asset_main)
        .def_readwrite("asset_sub", &DeepCycleEvent::asset_sub)
        .def_readwrite("metric", &DeepCycleEvent::metric)
        .def_readwrite("threshold", &DeepCycleEvent::threshold)
        .def_readwrite("timestamp", &DeepCycleEvent::timestamp);

    py::class_<MetaEvent>(m, "MetaEvent")
        .def(py::init<MetaBrainType, std::string, double, double, double>())
        .def_readwrite("type", &MetaEvent::type)
        .def_readwrite("target", &MetaEvent::target)
        .def_readwrite("value1", &MetaEvent::value1)
        .def_readwrite("value2", &MetaEvent::value2)
        .def_readwrite("timestamp", &MetaEvent::timestamp);

    // =========================================================================
    // 3. Analytics & Machine Learning Proxies
    // =========================================================================
    py::class_<Analytics>(m, "Analytics")
        .def_static("calculate_log_returns", &Analytics::CalculateLogReturns)
        .def_static("calculate_volatility", &Analytics::CalculateVolatility)
        .def_static("calculate_var", &Analytics::CalculateVaR)
        .def_static("calculate_es", &Analytics::CalculateES)
        .def_static("fit_linear_regression", &Analytics::FitLinearRegression);

    py::class_<OptimizationResult>(m, "OptimizationResult")
        .def_readonly("optimal_weights", &OptimizationResult::optimal_weights)
        .def_readonly("portfolio_return", &OptimizationResult::portfolio_return)
        .def_readonly("portfolio_volatility", &OptimizationResult::portfolio_volatility)
        .def_readonly("sharpe_ratio", &OptimizationResult::sharpe_ratio);

    py::class_<Optimizer>(m, "Optimizer")
        .def(py::init<>())
        .def("add_asset", &Optimizer::add_asset)
        .def("optimize_sharpe_ratio", &Optimizer::optimize_sharpe_ratio)
        .def("optimize_inverse_volatility", &Optimizer::optimize_inverse_volatility, py::arg("risk_free_rate") = 0.0)
        .def("optimize_minimum_variance", &Optimizer::optimize_minimum_variance, py::arg("risk_free_rate") = 0.0);

    py::class_<Gene>(m, "Gene")
        .def_readonly("fast", &Gene::fast)
        .def_readonly("slow", &Gene::slow)
        .def_readonly("signal", &Gene::signal)
        .def_readonly("fitness", &Gene::fitness);

    py::class_<GeneticOptimizer>(m, "GeneticOptimizer")
        .def_static("evolve_macd", &GeneticOptimizer::evolve_macd,
            py::arg("prices"), py::arg("initial_capital"),
            py::arg("generations") = 10, py::arg("population_size") = 50);

    py::class_<PairResult>(m, "PairResult")
        .def_readonly("asset_a", &PairResult::asset_a)
        .def_readonly("asset_b", &PairResult::asset_b)
        .def_readonly("correlation", &PairResult::correlation)
        .def_readonly("beta", &PairResult::beta)
        .def_readonly("r_squared", &PairResult::r_squared);

    py::class_<PairSelector>(m, "PairSelector")
        .def_static("find_top_pairs", &PairSelector::FindTopPairs,
            "Find the pair with highest correlation",
            py::arg("market_data"), py::arg("top_n") = 5);

    py::class_<LinearRegressionResult>(m, "LinearRegressionResult")
        .def_readonly("alpha", &LinearRegressionResult::alpha)
        .def_readonly("beta", &LinearRegressionResult::beta)
        .def_readonly("r_squared", &LinearRegressionResult::r_squared);

    py::class_<RegimeResult>(m, "RegimeResult")
        .def_readonly("state_id", &RegimeResult::state_id)
        .def_readonly("state_name", &RegimeResult::state_name)
        .def_readonly("current_volatility", &RegimeResult::current_volatility)
        .def_readonly("current_trend", &RegimeResult::current_trend);

    py::class_<RegimeDetector>(m, "RegimeDetector")
        .def_static("detect_regime", &RegimeDetector::DetectRegime,
            "Detect market regime using K-Means clustering",
            py::arg("prices"), py::arg("window_size") = 20);

    py::class_<PCAResult>(m, "PCAResult")
        .def_readonly("z_scores", &PCAResult::z_scores)
        .def_readonly("explained_variance", &PCAResult::explained_variance);

    py::class_<PCAArbitrage>(m, "PCAArbitrage")
        .def_static("calculate_signals", &PCAArbitrage::CalculateSignals,
            "Calculate PCA-based Stat-Arb Z-scores",
            py::arg("prices"), py::arg("num_components") = 1);

    py::class_<BSGreeks>(m, "BSGreeks")
        .def_readonly("delta", &BSGreeks::delta)
        .def_readonly("gamma", &BSGreeks::gamma)
        .def_readonly("theta", &BSGreeks::theta)
        .def_readonly("vega", &BSGreeks::vega)
        .def_readonly("rho", &BSGreeks::rho);

    py::class_<Trade>(m, "Trade")
        .def_readonly("id", &Trade::id)
        .def_readonly("symbol", &Trade::symbol)
        .def_readonly("side", &Trade::side)
        .def_readonly("quantity", &Trade::quantity)
        .def_readonly("price", &Trade::price)
        .def_readonly("commission", &Trade::commission)
        .def_readonly("timestamp", &Trade::timestamp);

    py::class_<OrderBook>(m, "OrderBook")
        .def(py::init<std::string>(), py::arg("symbol"))
        .def("add_order", &OrderBook::add_order, py::arg("order_id"), py::arg("price"), py::arg("quantity"), py::arg("is_buy"), py::arg("timestamp"))
        .def("cancel_order", &OrderBook::cancel_order, py::arg("order_id"), py::arg("timestamp"))
        .def("get_best_bid", &OrderBook::get_best_bid)
        .def("get_best_ask", &OrderBook::get_best_ask)
        .def("get_mid_price", & OrderBook::get_mid_price)
        .def("calculate_imbalance", &OrderBook::calculate_imbalance, py::arg("levels") = 5, "Calculate Order Book Imbalance (OBI)")
        .def("record_trade", &OrderBook::record_trade, py::arg("price"), py::arg("quantity"), py::arg("is_buy_initiated"), py::arg("timestamp"))
        .def("calculate_vpin", &OrderBook::calculate_vpin, py::arg("bucket_vol_size"), py::arg("num_buckets"))
        .def("calculate_vwap", &OrderBook::calculate_vwap)
        .def("clear_tape", &OrderBook::clear_tape)
        .def("modify_order", &OrderBook::modify_order, py::arg("order_id"), py::arg("new_quantity"), py::arg("timestamp"))
        .def("execute_trade", &OrderBook::execute_trade, py::arg("price"), py::arg("quantity"), py::arg("timestamp"));

    // =========================================================================
    // 4. The Grand C++ Backtester Engine 
    // =========================================================================
    py::class_<Backtester>(m, "Backtester")
        .def(py::init<double, std::string, double>(), 
            py::arg("initial_capital"),
            py::arg("strategy_type") = "EMA",
            py::arg("leverage") = 1.0)

        // Core Hooks
        .def("on_market_data", &Backtester::on_market_data, py::arg("symbol"), py::arg("timestamp"), py::arg("open"), py::arg("high"), py::arg("low"), py::arg("close"))
        .def("on_order_book_update", &Backtester::on_order_book_update, py::arg("book"), py::arg("timestamp"))
        .def("send_order", &Backtester::send_order, py::arg("symbol"), py::arg("side"), py::arg("quantity"), py::arg("price"), py::arg("timestamp"))

        // Advanced 75-Strategy Event Routers (The Bridge)
        .def("send_corporate_action", &Backtester::send_corporate_action)
        .def("send_microstructure_msg", &Backtester::send_microstructure_msg)
        .def("send_crypto_event", &Backtester::send_crypto_event)
        .def("send_alt_data", &Backtester::send_anomaly_event)
        .def("send_macro_event", &Backtester::send_macro_event)
        .def("send_ai_bhv_event", &Backtester::send_ai_bhv_event)
        .def("send_final_event", &Backtester::send_final_event)
        .def("send_l3_message", &Backtester::send_l3_message)
        .def("send_structural_event", &Backtester::send_structural_event)
        .def("send_deep_cycle_event", &Backtester::send_deep_cycle_event)
        .def("send_meta_event", &Backtester::send_meta_event)

        // Engine State Getters
        .def("get_holdings", &Backtester::get_holdings, py::arg("symbol"))
        .def("get_opens", &Backtester::get_opens, py::return_value_policy::reference, py::arg("symbol"))
        .def("get_highs", &Backtester::get_highs, py::return_value_policy::reference, py::arg("symbol"))
        .def("get_lows", &Backtester::get_lows, py::return_value_policy::reference, py::arg("symbol"))
        .def("get_closes", &Backtester::get_closes, py::return_value_policy::reference, py::arg("symbol"))
        .def("get_total_equity", &Backtester::get_total_equity)
        .def("get_cash_balance", &Backtester::get_cash_balance)
        .def("get_leverage", &Backtester::get_leverage)
        .def("get_trade_history", &Backtester::get_trade_history)
        .def("get_max_drawdown", &Backtester::get_max_drawdown)
        .def("get_equity_history", &Backtester::get_equity_history)

        // Control Parameters
        .def("set_risk_params", &Backtester::set_risk_params, py::arg("max_drawdown_limit") = 0.05, py::arg("var_limit") = 0.02)
        .def("set_pairs_parameters", &Backtester::set_pairs_parameters, py::arg("window"), py::arg("threshold"))
        .def("set_macd_parameters", &Backtester::set_macd_parameters)
        .def("set_volatility_k", &Backtester::set_volatility_k)
        .def("set_regime_filter", &Backtester::set_regime_filter, py::arg("use_filter"), py::arg("lookback") = 252);
}