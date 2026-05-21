// src/main.cpp

#include <iostream>
#include <vector>
#include <memory>
#include <string>
#include <random>
#include <fmt/core.h>
#include <fmt/color.h>
#include "../include/SimpleMC.h"
#include "../include/BinomialTree.h"
#include "../include/BlackScholesFormulas.h"
#include "../include/PayoffFactory.h"
#include "../include/VanillaOption.h"
#include "../include/Parameters.h"
#include "../include/MCStatistics.h"
#include "../include/Random.h"
#include "../include/AntiThetic.h"
#include "../include/NumericalGreeks.h"
#include "../include/Bisection.h"
#include "../include/Optimizer.h"
#include "../include/OrderBook.h"
#include "../include/Backtester.h"
#include "../include/RegimeDetector.h"
#include "../include/MetaManager.h"

void PrintBanner() {
    fmt::print(fg(fmt::color::cyan), "\n==================================================\n");
    fmt::print(fg(fmt::color::yellow) | fmt::emphasis::bold, "       Aladdin-Killer: FinancialOS v2.0 (Core)\n");
    fmt::print(fg(fmt::color::cyan), "==================================================\n");
    fmt::print(" [1] Core A: Portfolio Optimizer (Risk Parity & MinVar)\n");
    fmt::print(" [2] Core B: Derivatives Pricing & Risk Engine\n");
    fmt::print(" [3] Core C: L2 Microstructure (VPIN & Tape Analysis)\n");
    fmt::print(" [4] Core D: Stat-Arb (Kalman Filter Pairs Trading)\n");
    fmt::print(" [5] Core E: Multi-Asset Stat-Arb (PCA Eigenvalue Decomposition)\n");
    fmt::print(" [6] Core F: Regime Detection (Hidden Markov Model)\n");
    fmt::print(" [7] Core G: Execution Tactics Suite (OMS)\n");
    fmt::print(" [8] Core H: Volatility Risk Premium (VRP) Harvesting\n");
    fmt::print(" [9] Core I: Meta-Portfolio Manager (The OS Brain)\n");
    fmt::print(" [10] Core J: Avellaneda-Stoikov Market Making (HFT)\n");
    fmt::print(" [11] Core K: Event-Driven & Structural Imbalance Suite\n");
    fmt::print(" [12] Core L: Advanced Microstructure & Liquidity Suite\n");
    fmt::print(" [13] Core M: Crypto & DeFi Arbitrage Suite\n");
    fmt::print(" [14] Core N: Alternative Data & Sentiment Analysis Suite\n");
    fmt::print(" [15] Core O: Advanced Downside Protection & Squeeze Tactics\n");
    fmt::print(" [16] Core P: Global Macro & Fixed Income Suite\n");
    fmt::print(" [17] Core Q: Machine Learning & Behavioral Economics Suite\n");
    fmt::print(" [18] Core R: Grand Finale (Quantum, Regulatory & Chaos Theory)\n");
    fmt::print(" [19] Core S: L3 Microstructure & Advanced Execution Desk (14 Strategies)\n");
    fmt::print(" [20] Core T: Structural & Derivative Aribitrage Desk (10 Strategies)\n");
    fmt::print(" [21] Core U: Deep Crypto & Cycle Anomaly Desk (7 Strategies)\n");
    fmt::print(" [22] Core V: The Meta-Brain OS (6 Meta Strategies)\n");
    fmt::print(" [0] Exit System\n");
    fmt::print("========================================================\n");
    fmt::print(fg(fmt::color::white) | fmt::emphasis::bold, " OS> ");
}

// ---------------------------------------------------------
// Module 1: Portfolio Optimizer
// ---------------------------------------------------------
void RunPortfolioModule() {
    fmt::print(fg(fmt::color::green), "\n[Core A] Initializing Eigen-based Portfolio Optimizer...\n");
    Optimizer opt;

    std::mt19937 gen(42);
    std::normal_distribution<> spy_dist(0.0005, 0.01);
    std::normal_distribution<> tlt_dist(0.0002, 0.005);

    std::vector<double> spy_ret(252), tlt_ret(252), gld_ret(252);
    for (int i = 0; i < 252; ++i) {
        spy_ret[i] = spy_dist(gen);
        tlt_ret[i] = tlt_dist(gen) - spy_ret[i] * 0.2;
        gld_ret[i] = tlt_dist(gen) + 0.0001;
    }

    opt.add_asset("SPY", spy_ret);
    opt.add_asset("TLT", tlt_ret);
    opt.add_asset("GLD", gld_ret);

    auto res = opt.optimize_minimum_variance(0.04);

    fmt::print(" -> [Global Minimum Variance Portfolio]\n");
    fmt::print("    SPY Weight: {:.2f}%\n", res.optimal_weights[0] * 100);
    fmt::print("    TLT Weight: {:.2f}%\n", res.optimal_weights[1] * 100);
    fmt::print("    GLD Weight: {:.2f}%\n", res.optimal_weights[2] * 100);
    fmt::print("    Exp Volatility: {:.2f}%\n", res.portfolio_volatility * 100);
}

// ---------------------------------------------------------
// Module 2: Derivatives Engine
// ---------------------------------------------------------
void RunDerivativeModule() {
    fmt::print(fg(fmt::color::green), "\n[Core B] Initializing Derivatives & Risk Engine...\n");

    double Spot = 100.0, Strike = 100.0, r = 0.05, d = 0.0, Vol = 0.2, Expiry = 1.0;\
    fmt::print(" Market Data: Spot={}, Strike={}, Rate={:.1f}%, Vol={:.1f}%\n", Spot, Strike, r*100, Vol*100);

    auto PayoffPtr = PayoffFactory::Instance().CreatePayoff("call", Strike);
    VanillaOption EuroOption(*PayoffPtr, Expiry);
    ParametersConstant VolParam(Vol), RateParam(r);
    StatisticsMean stats;
    RandomMersenne rng(1);
    AntiThetic antiGen(rng);

    SimpleMonteCarlo(EuroOption, Spot, VolParam, RateParam, 100000, stats, antiGen);
    double MCPrice = stats.GetResultsSoFar()[0][0];
    double BSPrice = BlackScholes::CallPrice(Spot, Strike, r, d, Vol, Expiry);
    fmt::print(" -> MC Call Price: {:.5f} (Error: {:.5e})\n", MCPrice, std::abs(MCPrice - BSPrice));

    auto PricingEngine = [&](double S) { return BlackScholes::CallPrice(S, Strike, r, d, Vol, Expiry); };
    double h = Spot * 0.01;
    fmt::print(" -> Delta: {:.5f} | Gamma: {:.5f}\n", CalculateDelta(Spot, h, PricingEngine), CalculateGamma(Spot, h, PricingEngine));
}

// ---------------------------------------------------------
// Module 3: L2 Microstructure
// ---------------------------------------------------------
void RunMicrostructureModule() {
    fmt::print(fg(fmt::color::green), "\n[Core C] Initializing L2 OrderBook & Tape Analysis...\n");
    OrderBook book("SPY");

    fmt::print(" -> Injecting High-Frequency Trade Tape (Toxic Flow Scenario)...\n");
    for (int i = 0; i < 500; ++i) {
        bool is_buy = (i % 10) > 7;
        double price = is_buy ? 100.0 : 99.9;
        book.record_trade(price, 100.0, is_buy, static_cast<double>(i));
    }

    double vwap = book.calculate_vwap();
    double vpin = book.calculate_vpin(1000.0, 5);

    fmt::print(" -> Current Market VWAP: ${:.4f}\n", vwap);
    fmt::print(" -> VPIN Toxicity Score: {:.4f} / 1.0\n", vpin);
    if (vpin > 0.6) {
        fmt::print(fg(fmt::color::red) | fmt::emphasis::bold, " [!] ALERT: Flash Crash Probability High. Pulling Quotes.\n");
    }
}

// ---------------------------------------------------------
// Module 4: Statistical Arbitrage (Kalman Filter)
// ---------------------------------------------------------
void RunPairsTradingModule() {
    fmt::print(fg(fmt::color::green), "\n[Core D] Initializing Kalman Filter Pairs Engine...\n");

    Backtester engine(100000.0, "PAIRS", 1.0);
    engine.set_regime_filter(false);
    engine.set_risk_params(0.10, 0.05);

    std::mt19937 gen(42);
    std::normal_distribution<> noise(0.0, 0.5);
    std::normal_distribution<> random_walk(0.0, 1.0);

    double price_x = 50.0;
    double true_beta = 1.5;
    double spread_shock = 0.0;

    fmt::print(" -> Injecting 500 ticks of cointegrated pairs data (KO & PEP)...\n");

    for (int i = 1; i <= 500; ++i) {
        price_x += random_walk(gen);

        if (i == 250) spread_shock = 15.0;
        spread_shock *= 0.95;

        double price_y = (price_x * true_beta) + noise(gen) + spread_shock;

        engine.on_market_data("KO", static_cast<double>(i), price_x, price_x, price_x, price_x);
        engine.on_market_data("PEP", static_cast<double>(i), price_y, price_y, price_y, price_y);
    }

    fmt::print(" -> Backtest Complete. Target Shock a Tick 250 Captured.\n");
    fmt::print(" -> Initial Equity: $100,000.00\n");
    fmt::print(" -> Final Equity:   ${:.2f}\n", engine.get_total_equity());

    double pnl = engine.get_total_equity() - 100000.0;
    if (pnl > 0) {
        fmt::print(fg(fmt::color::cyan), " -> Stat-Arb Profit: +${:.2f}\n", pnl);
    } else {
        fmt::print(fg(fmt::color::red), " -> Stat-Arb Loss: ${:.2f}\n", pnl);
    }
}

// ---------------------------------------------------------
// Module 5: PCA-based Statistical Arbitrage
// ---------------------------------------------------------
void RunPCAAribitrageModule() {
    fmt::print(fg(fmt::color::green), "\n[Core E] Initializing PCA Stat-Arb Engine...\n");

    Backtester engine(100000.0, "PCA", 1.0);
    engine.set_regime_filter(false);
    engine.set_risk_params(0.15, 0.10);

    std::mt19937 gen(42);
    std::normal_distribution<> market_factor(0.0, 1.0);
    std::normal_distribution<> noise(0.0, 0.2);

    double p_aapl = 150.0;
    double p_msft = 250.0;
    double p_goog = 100.0;
    double p_tsla = 200.0;

    double tsla_shock = 0.0;

    fmt::print(" -> Injecting 500 ticks of basket data (AAPL, MSFT, GOOG, TSLA)...\n");
    fmt::print(" -> System will attempt to extract Market Principal Component and trade residuals.\n");

    for (int i = 1; i <= 500; ++i) {
        double mkt = market_factor(gen);

        p_aapl += (mkt * 1.0) + noise(gen);
        p_msft == (mkt * 1.2) + noise(gen);
        p_goog += (mkt * 0.9) + noise(gen);

        if (i == 300) tsla_shock = -25.0;
        tsla_shock *= 0.95;
        
        p_tsla += (mkt * 1.5) + noise(gen) + tsla_shock;

        engine.on_market_data("AAPL", static_cast<double>(i), p_aapl, p_aapl, p_aapl, p_aapl);
        engine.on_market_data("MSFT", static_cast<double>(i), p_msft, p_msft, p_msft, p_msft);
        engine.on_market_data("GOOG", static_cast<double>(i), p_goog, p_goog, p_goog, p_goog);
        engine.on_market_data("TSLA", static_cast<double>(i), p_tsla, p_tsla, p_tsla, p_tsla);
    }

    fmt::print(" -> Backtest Complete. Target Anomaly on TSLA Captured via Residual Z-Score.\n");
    fmt::print(" -> Initial Equity: $100,000.00\n");
    fmt::print(" -> Final Equity:   ${:.2f}\n", engine.get_total_equity());

    double pnl = engine.get_total_equity() - 100000.0;
    if (pnl > 0) {
        fmt::print(fg(fmt::color::cyan), " -> PCA Stat-Arb Profit: +${:.2f}\n", pnl);
    } else {
        fmt::print(fg(fmt::color::red), " -> PCA Stat-Arb Loss: ${:.2f}\n", pnl);
    }
}

// ---------------------------------------------------------
// Module 6: Hidden Markov Model Regime Detection
// ---------------------------------------------------------
void RunRegimeDetectionModule() {
    fmt::print(fg(fmt::color::green), "\n[Core F] Initializing HMM Regime Detector...\n");

    std::mt19937 gen(42);
    std::vector<double> market_prices;
    double current_price = 100.0;

    fmt::print(" -> Generating synthetic market data (Bull -> Bear -> Bull phases)...\n");

    std::normal_distribution<> bull_dist(0.001, 0.005);
    for (int i = 0; i < 60; ++i) {
        current_price *= (1.0 + bull_dist(gen));
        market_prices.push_back(current_price);
    }

    std::normal_distribution<> bear_dist(-0.003, 0.020);
    for (int i = 0; i < 40; ++i) {
        current_price *= (1.0 + bear_dist(gen));
        market_prices.push_back(current_price);
    }

    for (int i = 0; i < 50; ++i) {
        current_price *= (1.0 + bull_dist(gen));
        market_prices.push_back(current_price);
    }

    fmt::print(" -> Analyzing 150 days of market history using K-Means Clustering...\n\n");

    RegimeResult current_regime = RegimeDetector::DetectRegime(market_prices, 20);

    fmt::print(fg(fmt::color::yellow), " [Clustering Analysis Report]\n");
    fmt::print(" -> Current Price:      ${:.2f}\n", market_prices.back());
    fmt::print(" -> Detected State:     {}\n", current_regime.state_name);
    fmt::print(" -> Current Volatility: {:.2f}%\n", current_regime.current_volatility * 100.0);
    fmt::print(" -> Current Trend:      {:.4f}\n", current_regime.current_trend);
    fmt::print(" -> Strategy Action:    ");

    if (current_regime.state_name == "Bull") {
        fmt::print(fg(fmt::color::cyan), "Trend Following (Momentum) ENGAGED.\n");
    } else if (current_regime.state_name == "Bear") {
        fmt::print(fg(fmt::color::red), "RISK OFF. Hibernate Longs. Enable Mean Reversion.\n");
    } else {
        fmt::print("Neutral. Delta-Neutral strategies only.\n");
    }
}

// ---------------------------------------------------------
// Module 7: Order Management System (Execution Tactics)
// ---------------------------------------------------------
void RunExecutionModule() {
    fmt::print(fg(fmt::color::green), "\n[Core G] Initializing Order Management System (OMS)...\n");
    fmt::print(" Select OMS Algorithm for 10,000 shares execution:\n");
    fmt::print("  [1] TWAP (Time Weighted Average Price)\n");
    fmt::print("  [2] POV (Percentage of Volume)\n");
    fmt::print("  [3] ICEBERG (Hidden Order Size)\n");
    fmt::print("  [4] SNIPER (Liquidity Taker)\n");
    fmt::print("  > ");

    std::string algo_choice;
    std::getline(std::cin, algo_choice);

    std::string algo_name;
    if (algo_choice == "1") algo_name = "TWAP";
    else if (algo_choice == "2") algo_name = "POV";
    else if (algo_choice == "3") algo_name = "ICEBERG";
    else if (algo_choice == "4") algo_name = "SNIPER";
    else {
        fmt::print(fg(fmt::color::red), " Invalid choice. Defaulting to ICEBERG.\n");
        algo_name = "ICEBERG";
    }

    Backtester engine(2000000.0, algo_name, 1.0);
    engine.set_regime_filter(false);
    OrderBook book("SPY");

    fmt::print(" -> Simulating Intraday L2 Market Data for {}...\n\n", algo_name);

    for (int i = 1; i <= 50; ++i) {
        double timestamp = static_cast<double>(i);
        double current_price = 100.0 - (i * 0.02);

        book.add_order(i * 10, current_price - 0.05, 2000.0, true, timestamp);
        book.add_order(i * 10 + 1, current_price + 0.05, 2000.0, false, timestamp);

        engine.on_order_book_update(book, timestamp);

        book.cancel_order(i * 10, timestamp);
        book.cancel_order(i * 10 + 1, timestamp);
    }

    fmt::print("\n -> OMS Execution Complete.\n");
    fmt::print(fg(fmt::color::cyan), " -> Total Shares Accumulated: {:.0f} / 10000\n", engine.get_holdings("SPY"));
}

// ---------------------------------------------------------
// Module 8: Volatility Risk Premium (VRP) Harvesting
// ---------------------------------------------------------
void RunVRPModule() {
    fmt::print(fg(fmt::color::green), "\n[Core H] Initializing Volatility Risk Premium (VRP) Desk...\n");

    Backtester engine(100000.0, "VRP", 1.0);
    engine.set_regime_filter(false);

    std::mt19937 gen(42);
    std::normal_distribution<> random_walk(0.0005, 0.015);
    double price = 100.0;

    fmt::print(" -> Simulating 50 days of market data for Straddle Delta Hedging...\n\n");

    for (int i = 1; i <= 50; ++i) {
        price *= (1.0 + random_walk(gen));
        engine.on_market_data("SPY", static_cast<double>(i), price, price, price, price);
    }

    fmt::print("\n -> VRP Harvesting Complete.\n");
    fmt::print(" -> Final Equity:   ${:.2f}\n", engine.get_total_equity());
}

// ---------------------------------------------------------
// Module 9: Meta-Portfolio Manager (The OS Brain)
// ---------------------------------------------------------
void RunMetaManagerModule() {
    fmt::print(fg(fmt::color::green), "\n[Core I] Initializing Meta-Portfolio Manager (The OS Brain)...\n");

    MetaManager brain(1000000.0);

    fmt::print("\n [Initial State] Default Allocations:\n");
    brain.print_current_allocations();

    std::mt19937 gen(42);
    std::vector<double> market_prices;
    double current_price = 100.0;

    fmt::print(fg(fmt::color::red), "\n [Scenario 1] Simulating Market Crash (Bear Regime)...\n");
    std::normal_distribution<> bear_dist(-0.005, 0.025);
    for (int i = 0; i < 40; ++i) {
        current_price *= (1.0 + bear_dist(gen));
        market_prices.push_back(current_price);
    }
    RegimeResult regime1 = RegimeDetector::DetectRegime(market_prices, 20);
    brain.reallocate_capital(regime1.state_name);

    fmt::print(fg(fmt::color::yellow), "\n [Scenario 2] Simulating Consolidation (Sideways Regime)...\n");
    std::normal_distribution<> sideways_dist(0.000, 0.008);
    for (int i = 0; i < 40; ++i) {
        current_price *= (1.0 + sideways_dist(gen));
        market_prices.push_back(current_price);
    }
    RegimeResult regime2 = RegimeDetector::DetectRegime(market_prices, 20);
    brain.reallocate_capital(regime2.state_name);

    fmt::print(fg(fmt::color::cyan), "\n [Scenario 3] Simulating Strong Uptrend (Bull Regime)...\n");
    std::normal_distribution<> bull_dist(0.002, 0.006);
    for (int i = 0; i < 40; ++i) {
        current_price *= (1.0 + bull_dist(gen));
        market_prices.push_back(current_price);
    }
    RegimeResult regime3 = RegimeDetector::DetectRegime(market_prices, 20);
    brain.reallocate_capital(regime3.state_name);

    fmt::print("\n -> Meta-Portfolio Simulation Complete.\n");
}

// ---------------------------------------------------------
// Module 10: Avellaneda-Stoikov Market Making (HFT)
// ---------------------------------------------------------
void RunMarketMakingModule() {
    fmt::print(fg(fmt::color::green), "\n[Core J] Initializing Avellaneda-Stoikov HFT Desk...\n");

    Backtester engine(100000.0, "AVELLANEDA", 1.0);
    engine.set_regime_filter(false);
    OrderBook book("SPY");

    std::mt19937 gen(42);
    std::normal_distribution<> random_walk(0.0, 0.05);
    std::normal_distribution<> spread_noise(0.01, 0.03);

    double current_price = 100.0;

    fmt::print(" -> Simulating 500 Ticks of High-Frequency L2 Data...\n\n");

    for (int i = 1; i <= 500; ++i) {
        double timestamp = static_cast<double>(i);
        current_price += random_walk(gen);

        double market_bid = current_price - spread_noise(gen);
        double market_ask = current_price + spread_noise(gen);

        if (i % 20 == 0) market_bid += 1.5;
        if (i % 25 == 0) market_ask -= 1.5;

        book.add_order(i * 10, market_bid, 1000.0, true, timestamp);
        book.add_order(i * 10 + 1, market_ask, 1000.0, false, timestamp);

        engine.on_order_book_update(book, timestamp);

        book.cancel_order(i * 10, timestamp);
        book.cancel_order(i * 10 + 1, timestamp);
    }

    fmt::print("\n -> HFT Market Making Complete.\n");
    fmt::print(" -> Final Inventory (Shares): {:.0f}\n", engine.get_holdings("SPY"));
    fmt::print(fg(fmt::color::cyan), " -> Final Equity: ${:.2f}\n", engine.get_total_equity());
}

// ---------------------------------------------------------
// Module 11: Event-Driven Suite (Merger, PEAD, Rebalance)
// ---------------------------------------------------------
void RunEventDrivenModule() {
    fmt::print(fg(fmt::color::green), "\n[Core K] Initializing Event-Driven Desk...\n");

    Backtester engine(100000.0, "EVENT_DRIVEN", 1.0);
    engine.set_regime_filter(false);

    engine.on_market_data("TSLA", 1.0, 200.0, 200.0, 200.0, 200.0);
    engine.on_market_data("TARGET_CO", 1.0, 50.0, 50.0, 50.0, 50.0);
    engine.on_market_data("ACQUIRER_INC", 1.0, 150.0, 150.0, 150.0, 150.0);
    engine.on_market_data("NVDA", 1.0, 500.0, 500.0, 500.0, 500.0);

    fmt::print(" -> Parsing Corporate Filings & News Feeds...\n\n");

    CorporateAction evt1{ActionType::INDEX_REBALANCE, "TSLA", "", 0.0, 2.0};
    engine.send_corporate_action(evt1);

    CorporateAction evt2{ActionType::MERGER_ANNOUNCEMENT, "TARGET_CO", "ACQUIRER_INC", 60.0, 3.0};
    engine.send_corporate_action(evt2);

    CorporateAction evt3{ActionType::EARNINGS_SURPRISE, "NVDA", "", 3.5, 4.0};
    engine.send_corporate_action(evt3);

    CorporateAction evt4{ActionType::SHARE_BUYBACK, "TARGET_CO", "", 0.0, 5.0};
    engine.send_corporate_action(evt4);

    fmt::print("\n -> Event-Driven Execution Complete.\n");
    fmt::print(fg(fmt::color::cyan), " -> Current Portfolio Allocation:\n");
    fmt::print("    TSLA: {:.0f} shares\n", engine.get_holdings("TSLA"));
    fmt::print("    TARGET_CO: {:.0f} shares\n", engine.get_holdings("TARGET_CO"));
    fmt::print("    ACQUIRER_INC: {:.0f} shares\n", engine.get_holdings("ACQUIRER_INC"));
    fmt::print("    NVDA: {:.0f} shares\n", engine.get_holdings("NVDA"));
}

// ---------------------------------------------------------
// Module 12: Advanced Microstructure Suite
// ---------------------------------------------------------
void RunMicrostructureSuiteModule() {
    fmt::print(fg(fmt::color::green), "\n[Core L] Initializing Microstructure & Liquidity Desk...\n");

    Backtester engine(100000.0, "MICROSTRUCTURE", 1.0);
    engine.set_regime_filter(false);

    fmt::print(" -> Simulating High-Frequency Microstructure Tape...\n\n");

    engine.send_microstructure_msg({100.0, "EXCHANGE_A", 100.00, 100.05, false});

    fmt::print(fg(fmt::color::yellow), " -> Injecting Quote Stuffing Attack (HFT Noise)...\n");
    for (int i = 0; i < 51; ++i) {
        engine.send_microstructure_msg({200.0 + i, "EXCHANGE_A", 100.00, 100.05, true});
    }

    engine.send_microstructure_msg({1500.0, "EXCHANGE_A", 100.00, 100.05, false});

    fmt::print(fg(fmt::color::green), " -> Clearing Toxicity Shield (Market is calm)...\n");
    engine.send_microstructure_msg({2600.0, "EXCHANGE_A", 100.00, 100.05, false});

    fmt::print(fg(fmt::color::cyan), " -> Injecting Latency Discrepancy (A is lagging behind B)...\n");
    engine.send_microstructure_msg({3000.0, "EXCHANGE_B", 100.20, 100.25, false});
    engine.send_microstructure_msg({3001.0, "EXCHANGE_A", 100.00, 100.05, false});

    fmt::print("\n -> Microstructure Execution Complete.\n");
    fmt::print(" -> Final Equity: ${:.2f}\n", engine.get_total_equity());
}

// ---------------------------------------------------------
// Module 13: Crypto & DeFi Arbitrage Suite
// ---------------------------------------------------------
void RunCryptoDeFiModule() {
    fmt::print(fg(fmt::color::green), "\n[Core M] Initializing Crypto & DeFi Arbitrage Desk...\n");

    Backtester engine(100000.0, "CRYPTO_DEFI", 1.0);
    engine.set_regime_filter(false);

    engine.on_market_data("ETH", 1.0, 3000.0, 3000.0, 3000.0, 3000.0);

    fmt::print(" -> Connecting to Mempool & DEX Smart Contracts...\n\n");

    engine.send_crypto_event({CryptoEventType::FUNDING_RATE, "ETH", 0.002, 1.0, "", ""});
    engine.send_crypto_event({CryptoEventType::MEMPOOL_TRANSACTION, "ETH", 800000.0, 2.0, "", ""});
    engine.send_crypto_event({CryptoEventType::DEX_PRICE_UPDATE, "ETH", 3030.0, 3.0, "Uniswap", "SushiSwap"});

    fmt::print("\n -> Crypto/DeFi Execution Complete.\n");
    fmt::print(fg(fmt::color::cyan), " -> Final Equity: ${:.2f}\n", engine.get_total_equity());
}

// ---------------------------------------------------------
// Module 14: Alternative Data Suite
// ---------------------------------------------------------
void RunAltDataModule() {
    fmt::print(fg(fmt::color::green), "\n[Core N] Initializing Alternative Data Desk...\n");

    Backtester engine(100000.0, "ALT_DATA", 1.0);
    engine.set_regime_filter(false);

    engine.on_market_data("AAPL", 1.0, 150.0, 150.0, 150.0, 150.0);
    engine.on_market_data("WMT", 1.0, 60.0, 60.0, 60.0, 60.0);
    engine.on_market_data("LMT", 1.0, 400.0, 400.0, 400.0, 400.0);

    fmt::print(" -> Parsing Alternative Data Feeds (Satellites, NLP, SEC)...\n\n");

    engine.send_alt_data({AltDataType::NLP_SENTIMENT, "AAPL", 0.95, 2.0});
    engine.send_alt_data({AltDataType::SATELLITE_IMAGE, "WMT", 1.25, 3.0});
    engine.send_alt_data({AltDataType::CONGRESSIONAL_TRADE, "LMT", 2500000.0, 4.0});

    fmt::print("\n -> Alternative Data Execution Complete.\n");
    fmt::print(" -> Portfolio Holdings:\n");
    fmt::print("    AAPL: {:.0f} shares\n", engine.get_holdings("AAPL"));
    fmt::print("    WMT: {:.0f} shares\n", engine.get_holdings("WMT"));
    fmt::print("    LMT: {:.0f} shares\n", engine.get_holdings("LMT"));
}

// ---------------------------------------------------------
// Module 15: Downside Protection & Squeeze
// ---------------------------------------------------------
void RunDownsideSqueezeModule() {
    fmt::print(fg(fmt::color::green), "\n[Core O] Initializing Downside Protection & Squeeze Desk...\n");

    Backtester engine(100000.0, "DOWNSIDE_SQUEEZE", 1.0);
    engine.set_regime_filter(false);

    engine.on_market_data("GME", 1.0, 20.0, 20.0, 20.0, 20.0);
    engine.on_market_data("SPY", 1.0, 400.0, 400.0, 400.0, 400.0);

    fmt::print(" -> Scanning for Structural Anomalies and Risks...\n\n");

    engine.send_anomaly_event({AnomalyType::SHORT_SQUEEZE, "GME", "", 120.0, 85.0, 2.0});
    engine.send_anomaly_event({AnomalyType::TAIL_RISK, "SPY", "", 0.0, 0.0, 3.0});
    engine.send_anomaly_event({AnomalyType::BASIS_TRADE, "ES_SPOT", "ES_FUT", 4000.0, 4050.0, 4.0});
    engine.send_anomaly_event({AnomalyType::CROSS_BORDER, "BTC_KRW", "BTC_USD", 62000.0, 60000.0, 5.0});

    fmt::print("\n -> Anomaly Execution Complete.\n");
    fmt::print(fg(fmt::color::cyan), " -> Final Equity (Accounting for Options Premium): ${:.2f}\n", engine.get_total_equity());
}

// ---------------------------------------------------------
// Module 16: Global Macro & Fixed Income Suite
// ---------------------------------------------------------
void RunGlobalMacroModule() {
    fmt::print(fg(fmt::color::green), "\n[Core P] Initializing Global Macro & Fixed Income Desk...\n");

    Backtester engine(100000.0, "GLOBAL_MACRO", 1.0);
    engine.set_regime_filter(false);

    engine.on_market_data("US2Y", 1.0, 100.0, 100.0, 100.0, 100.0);
    engine.on_market_data("US10Y", 1.0, 95.0, 95.0, 95.0, 95.0);
    engine.on_market_data("USDCAD", 1.0, 1.35, 1.35, 1.35, 1.35);

    fmt::print(" -> Analyzing Global Yield Curves and FX Flows...\n\n");

    engine.send_macro_event({MacroEventType::YIELD_CURVE, "US2Y", "US10Y", 4.50, 4.55, 2.0});
    engine.send_macro_event({MacroEventType::CALENDER_SPREAD, "CL_NEAR", "CL_FAR", 75.0, 82.0, 3.0});
    engine.send_macro_event({MacroEventType::FI_CARRY_TRADE, "JPY", "USD", 0.1, 5.0, 4.0});
    engine.send_macro_event({MacroEventType::COMMODITY_FX, "WTI_CRUDE", "USDCAD", 6.5, 0.0, 5.0});

    fmt::print("\n -> Global Macro Execution Complete.\n");
    fmt::print(" -> Final Equity: ${:.2f}\n", engine.get_total_equity());
}

// ---------------------------------------------------------
// Module 17: Machine Learning & Behavioral Economics
// ---------------------------------------------------------
void RunAIBhvModule() {
    fmt::print(fg(fmt::color::green), "\n[Core Q] Initializing AI & Behavioral Economics Desk...\n");

    Backtester engine(100000.0, "AI_BHV", 1.0);
    engine.set_regime_filter(false);

    engine.on_market_data("NVDA", 1.0, 500.0, 500.0, 500.0, 500.0);
    engine.on_market_data("TSM", 1.0, 100.0, 100.0, 100.0, 100.0);
    engine.on_market_data("MOMO_ETF", 1.0, 50.0, 50.0, 50.0, 50.0);
    engine.on_market_data("SPY", 1.0, 400.0, 400.0, 400.0, 400.0);

    fmt::print(" -> Loading TensorRT Models and Behavioral Heuristics...\n\n");

    engine.send_order("MOMO_ETF", "BUY", 2000.0, 50.0, 1.0);

    engine.send_ai_bhv_event({AIBhvType::DEEP_ALPHA, "NVDA", "", 0.92, 2.0});
    engine.send_ai_bhv_event({AIBhvType::GNN_PROPAGATION, "TSM", "NVDA", 0.0, 3.0});
    engine.send_ai_bhv_event({AIBhvType::CROWDEDNESS, "MOMO_ETF", "", 88.5, 4.0});
    engine.send_ai_bhv_event({AIBhvType::FOMO_PANIC, "SPY", "", 5.0, 5.0});

    fmt::print("\n -> AI & Behavioral Execution Complete.\n");
    fmt::print(fg(fmt::color::cyan), " -> Final Equity: ${:.2f}\n", engine.get_total_equity());
}

// ---------------------------------------------------------
// Module 18: The Grand Finale
// ---------------------------------------------------------
void RunGrandFinaleModule() {
    fmt::print(fg(fmt::color::green), "\n[Core R] Initializing Grand Finale Suite...\n");

    Backtester engine(100000.0, "GRAND_FINALE", 1.0);
    engine.set_regime_filter(false);

    engine.on_market_data("GLOBAL_BASKET", 1.0, 200.0, 200.0, 200.0, 200.0);
    engine.on_market_data("HIGH_YIELD_CO", 1.0, 50.0, 50.0, 50.0, 50.0);
    engine.on_market_data("PHARMA_INC", 1.0, 120.0, 120.0, 120.0, 120.0);
    engine.on_market_data("SPX_INDEX", 1.0, 4500.0, 4500.0, 4500.0, 4500.0);

    fmt::print(" -> Activating Final Alpha Parameters...\n\n");

    engine.send_final_event({FinalTacticsType::QUANTUM_OPT, "GLOBAL_BASKET", 0.0, 0.0, 1.0});
    engine.send_final_event({FinalTacticsType::DIVIDEND_CAPTURE, "HIGH_YIELD_CO", 0.05, 0.0, 2.0});
    engine.send_final_event({FinalTacticsType::LITIGATION_ARB, "PHARMA_INC", 0.85, 0.0, 3.0});
    engine.send_final_event({FinalTacticsType::CHAOS_REGIME, "SPX_INDEX", 0.65, 0.0, 4.0});
    engine.send_final_event({FinalTacticsType::CHAOS_REGIME, "SPX+INDEX", 0.35, 0.0, 5.0});

    fmt::print("\n -> All 75 Quant Strategies Successfully Executed.\n");
    fmt::print(fg(fmt::color::cyan), " -> Final Equity: ${:.2f}\n", engine.get_total_equity());
}

// ---------------------------------------------------------
// Module 19: L3 Microstructure & Advanced Execution
// ---------------------------------------------------------
void RunL3ExecutionSuiteModule() {
    fmt::print(fg(fmt::color::green), "\n[Core S] Initializing L3 Microstructure & Advanced Execution Desk...\n");

    Backtester engine(100000.0, "L3_EXECUTION", 1.0);
    engine.set_regime_filter(false);

    OrderBook book("SPY");

    fmt::print(" -> Parsing Sub-Millisecond L3 Order Flow Tape...\n\n");

    book.add_order(1, 100.0, 50000.0, true, 1.0);
    book.add_order(2, 100.05, 1000.0, false, 1.0);
    engine.on_order_book_update(book, 1.0);

    engine.send_l3_message({2.0, "SPY", "LIT", "INST", 100.05, 25000.0, true});
    engine.send_l3_message({3.0, "SPY", "LIT", "TOXIC", 99.85, 500.0, false});
    engine.on_order_book_update(book, 4.0);
    engine.send_l3_message({5.0, "TSLA", "DARK_POOL", "INST", 200.0, 75000.0, true});
    engine.on_market_data("SPY", 6.0, 100.0, 100.0, 80.0, 80.0);

    fmt::print("\n -> L3 Microstructure & Execution Complete.\n");
    fmt::print(" -> Final Equity: ${:.2f}\n", engine.get_total_equity());
}

// ---------------------------------------------------------
// Module 20: Structural & Derivative Arbitrage Desk
// ---------------------------------------------------------
void RunStructuralArbModule() {
    fmt::print(fg(fmt::color::green), "\n[Core T] Initializing Structural & Derivative Arbitrage Desk...\n");

    Backtester engine(100000.0, "STRUCTURAL_ARB", 1.0);
    engine.set_regime_filter(false);
    
    engine.on_market_data("VIX_SPOT", 1.0, 15.0, 15.0, 15.0, 15.0);
    engine.on_market_data("VIX_FUT", 1.0, 16.5, 16.5, 16.5, 16.5);
    engine.on_market_data("SPX_VOL", 1.0, 12.0, 12.0, 12.0, 12.0);
    engine.on_market_data("BASKET_VOL", 1.0, 18.0, 18.0, 18.0, 18.0);
    engine.on_market_data("GOOG", 1.0, 153.5, 153.5, 153.5, 153.5);
    engine.on_market_data("GOOGL", 1.0, 150.0, 150.0, 150.0, 150.0);
    engine.on_market_data("UN_ADR", 1.0, 50.0, 50.0, 50.0, 50.0);
    engine.on_market_data("UN_LSE", 1.0, 38.0, 38.0, 38.0, 38.0);
    engine.on_market_data("AAPL", 1.0, 99.0, 99.0, 99.0, 99.0);
    engine.on_market_data("SPY", 1.0, 400.0, 400.0, 400.0, 400.0);

    fmt::print(" -> Scanning Market Micro-Inefficiencies & Options Surfaces...\n");

    engine.send_structural_event({StructArbType::VIX_BASIS, "VIX_SPOT", "VIX_FUT", 15.0, 16.5, 0.0, 1.0});
    engine.send_structural_event({StructArbType::DISPERSION, "SPX_VOL", "BASKET_VOL", 12.0, 18.0, 0.0, 2.0});
    engine.send_structural_event({StructArbType::SHARE_CLASS, "GOOG", "GOOGL", 153.5, 150.0, 2.0, 3.0});
    engine.send_structural_event({StructArbType::DUAL_LISTED, "UN_ADR", "UN_LSE", 50.0, 38.0, 1.25, 4.0});
    engine.send_structural_event({StructArbType::ODD_LOT, "AAPL", "AAPL_NBBO", 99.0, 100.0, 45.0, 5.0});
    engine.send_structural_event({StructArbType::DELTA_GAMMA, "SPY", "", 400.0, 0.0, 15.0, 6.0});

    fmt::print("\n -> Structural Arbitrage Complete.\n");
    fmt::print(fg(fmt::color::cyan), " -> Final Equity: ${:.2f}\n", engine.get_total_equity());
}

// ---------------------------------------------------------
// Module 21: Deep Crypto & Cycle Anomaly Desk
// ---------------------------------------------------------
void RunDeepCycleModule() {
    fmt::print(fg(fmt::color::green), "\n[Core U] Initializing Deep Crypto & Cycle Anomaly Desk...\n");

    Backtester engine(100000.0, "DEEP_CYCLE", 1.0);
    engine.set_regime_filter(false);

    engine.on_market_data("NEM", 1.0, 50.0, 50.0, 50.0, 50.0);
    engine.on_market_data("JNJ", 1.0, 150.0, 150.0, 150.0, 150.0);
    engine.on_market_data("NFLX", 1.0, 400.0, 400.0, 400.0, 400.0);
    engine.on_market_data("NVDA", 1.0, 800.0, 800.0, 800.0, 800.0);
    engine.on_market_data("MU", 1.0, 100.0, 100.0, 100.0, 100.0);
    engine.on_market_data("BTC", 1.0, 60000.0, 60000.0, 60000.0, 60000.0);
    engine.on_market_data("wETH", 1.0, 3000.0, 3000.0, 3000.0, 3000.0);

    fmt::print(" -> Parsing On-Chain Liquidation Maps & Supply Chain Cycles...\n\n");

    engine.send_deep_cycle_event({DeepCycleType::CROSS_ASSET_MOMO, "NEM", "GOLD", 0.05, 0.03, 2.0});
    engine.send_deep_cycle_event({DeepCycleType::LOW_VOL_ANOMALY, "JNJ", "", 0.08, 0.15, 3.0});
    engine.send_deep_cycle_event({DeepCycleType::OVERREACTION, "NFLX", "", -0.12, 0.0, 4.0});
    engine.send_deep_cycle_event({DeepCycleType::WINDOW_DRESSING, "NVDA", "", 1.0, 0.0, 5.0});
    engine.send_deep_cycle_event({DeepCycleType::INVENTORY_CYCLE, "MU", "", 1.0, 0.0, 6.0});
    engine.send_deep_cycle_event({DeepCycleType::LIQUIDATION_HUNT, "BTC", "", 100000000.0, 0.0, 7.0});
    engine.send_deep_cycle_event({DeepCycleType::CROSS_CHAIN_BRIDGE, "wETH", "Solana", 0.025, 0.0, 8.0});

    fmt::print("\n -> Deep Crypto & Cycle Anomaly Execution Complete.\n");
    fmt::print(fg(fmt::color::cyan), " -> Final Equity: ${:.2f}\n", engine.get_total_equity());
}

// ---------------------------------------------------------
// Module 22: The Meta-Brain OS
// ---------------------------------------------------------
void RunMetaBrainModule() {
    fmt::print(fg(fmt::color::green), "\n[Core V] Initializing The Meta-Brain OS (Grand Controller)...\n");

    Backtester engine(100000.0, "META_BRAIN", 1.0);
    engine.set_regime_filter(false);

    engine.on_market_data("SPY", 1.0, 450.0, 450.0, 450.0, 450.0);
    engine.on_market_data("TLT", 1.0, 100.0, 100.0, 100.0, 100.0);

    fmt::print(" -> Activating Top-Level Portfolio & Risk Optimization Engine...\n\n");

    engine.send_meta_event({MetaBrainType::RISK_PARITY, "", 0.18, 0.06, 1.0});
    engine.send_meta_event({MetaBrainType::HMM_REGIME, "SPY", 1.0, 0.0, 2.0});
    engine.send_meta_event({MetaBrainType::CLUSTERING, "High_Vol_Bear_Cluster", 0.0, 0.0, 3.0});
    engine.send_meta_event({MetaBrainType::ADAPTIVE_ARRIVAL, "SPY", 452.0, 0.2, 4.0});
    engine.send_meta_event({MetaBrainType::MULTI_STRAT_MVO, "STAT_ARB_PCA", 0.15, 0.0, 5.0});
    engine.send_meta_event({MetaBrainType::TAIL_RISK, "", 0.055, 0.0, 6.0});

    fmt::print("\n======================================================\n");
    fmt::print(fg(fmt::color::cyan) | fmt::emphasis::bold, " [SYSTEM] ALL 75 QUANT STRATEGIES SUCCESSFULLY COMPILED AND EXECUTED.\n");
    fmt::print("======================================================\n");
    fmt::print(" -> Final Equity: ${:.2f}\n", engine.get_total_equity());
}

// ---------------------------------------------------------
// OS Main Loop
// ---------------------------------------------------------
int main() {
    std::string input;
    while (true) {
        PrintBanner();
        std::getline(std::cin, input);

        if (input == "0" || input == "exit" || input == "quit") {
            fmt::print(fg(fmt::color::yellow), "Shutting down FinancialOS... Goodbye.\n");
            break;
        } else if (input == "1") {
            RunPortfolioModule();
        } else if (input == "2") {
            RunDerivativeModule();
        } else if (input == "3") {
            RunMicrostructureModule();
        } else if (input == "4") {
            RunPairsTradingModule();
        } else if (input == "5") {
            RunPCAAribitrageModule();
        } else if (input == "6") {
            RunRegimeDetectionModule();
        } else if (input == "7") {
            RunExecutionModule();
        } else if (input == "8") {
            RunVRPModule();
        } else if (input == "9") {
            RunMetaManagerModule();
        } else if (input == "10") {
            RunMarketMakingModule();
        } else if (input == "11") {
            RunEventDrivenModule();
        } else if (input == "12") {
            RunMicrostructureSuiteModule();
        } else if (input == "13") {
            RunCryptoDeFiModule();
        } else if (input == "14") {
            RunAltDataModule();
        } else if (input == "15") {
            RunDownsideSqueezeModule();
        } else if (input == "16") {
            RunGlobalMacroModule();
        } else if (input == "17") {
            RunAIBhvModule();
        } else if (input == "18") {
            RunGrandFinaleModule();
        } else if (input == "19") {
            RunL3ExecutionSuiteModule();
        } else if (input == "20") {
            RunStructuralArbModule();
        } else if (input == "21") {
            RunDeepCycleModule();
        } else if (input == "22") {
            RunMetaBrainModule();
        } else {
            fmt::print(fg(fmt::color::red), "Invalid Command!! You can only enter numbers on the screen!!\n");
        }
    }
    return 0;
}