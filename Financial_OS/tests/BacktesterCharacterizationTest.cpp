// tests/BacktesterCharacterizationTest.cpp
//
// CHARACTERIZATION TEST (a.k.a. "golden master" test).
//
// Backtester.cpp (~1,600 lines) currently has zero automated coverage. Before
// refactoring it (Phase 2) we pin its CURRENT behaviour so any unintended change
// shows up as a failing test. We are NOT asserting the behaviour is "correct" --
// only that it does not change while we restructure the code.
//
// ONE-TIME GOLDEN CAPTURE:
//   1. Build, then run:
//        ./build/tests/UnitTests --gtest_filter=BacktesterCharacterization.*
//   2. The test prints lines like  [GOLDEN] equity=... mdd=... trades=...
//   3. Copy those numbers into the kGolden* constants below.
//   4. Re-run -- it should now pass. Commit the locked-in values.
//
// After that, the test fails the moment a refactor changes engine output.

#include <gtest/gtest.h>

#include <cmath>
#include <iomanip>
#include <iostream>
#include <vector>

#include "Backtester.h"

namespace {

// Deterministic, RNG-free price series so the golden values are reproducible
// on every machine and compiler.
std::vector<double> MakeDeterministicSeries(int n) {
    std::vector<double> prices;
    prices.reserve(n);
    double price = 100.0;
    for (int i = 0; i < n; ++i) {
        const double drift = 0.0005 * price;
        const double wiggle = 2.0 * std::sin(i * 0.30) + 0.7 * std::cos(i * 0.11);
        price += drift + wiggle;
        if (price < 1.0) price = 1.0;
        prices.push_back(price);
    }
    return prices;
}

struct Golden {
    double equity;
    double max_drawdown;
    std::size_t trades;
};

Golden RunEngine(const std::string& strategy) {
    const double initial_capital = 100000.0;
    Backtester engine(initial_capital, strategy, 1.0);

    const std::vector<double> closes = MakeDeterministicSeries(300);
    for (std::size_t t = 0; t < closes.size(); ++t) {
        const double c = closes[t];
        // Treat each close as a flat OHLC bar -- enough for trend strategies.
        engine.on_market_data("TEST", static_cast<double>(t), c, c, c, c);
    }

    return {engine.get_total_equity(), engine.get_max_drawdown(),
            engine.get_trade_history().size()};
}

void PrintAndCheck(const char* label, const Golden& actual, const Golden& expected) {
    std::cout << "[GOLDEN] " << label << " equity=" << std::setprecision(12)
              << actual.equity << " mdd=" << actual.max_drawdown
              << " trades=" << actual.trades << "\n";

    EXPECT_NEAR(actual.equity, expected.equity, 1e-6) << label << " equity drifted";
    EXPECT_NEAR(actual.max_drawdown, expected.max_drawdown, 1e-9) << label << " mdd drifted";
    EXPECT_EQ(actual.trades, expected.trades) << label << " trade count drifted";
}

// === GOLDEN VALUES: replace the zeros after the one-time capture run ===
constexpr Golden kGoldenMacd{101384.315319, -0.0290943202974, 25};
constexpr Golden kGoldenEma{96344.2405722, -0.0534577610436, 4};

Golden RunMetaEvents() {
    Backtester engine(100000.0, "META_BRAIN", 1.0);
    engine.send_event(MetaEvent{MetaBrainType::RISK_PARITY, "", 0.18, 0.06, 1.0});
    engine.send_event(MetaEvent{MetaBrainType::HMM_REGIME, "SPY", 1.0, 0.0, 2.0});
    engine.send_event(MetaEvent{MetaBrainType::CLUSTERING, "High_Vol_Bear_Cluster", 0.0, 0.0, 3.0});
    engine.send_event(MetaEvent{MetaBrainType::ADAPTIVE_ARRIVAL, "SPY", 452.0, 0.2, 4.0});
    engine.send_event(MetaEvent{MetaBrainType::MULTI_STRAT_MVO, "STAT_ARB_PCA", 0.15, 0.0, 5.0});
    engine.send_event(MetaEvent{MetaBrainType::TAIL_RISK, "", 0.055, 0.0, 6.0});
    return {engine.get_total_equity(), engine.get_max_drawdown(), engine.get_trade_history().size()};
}

Golden RunStructuralEvents() {
    Backtester engine(100000.0, "STRUCTURAL_ARB", 1.0);
    engine.send_event(StructuralEvent{StructArbType::VIX_BASIS, "VIX_SPOT", "VIX_FUT", 15.0, 16.5, 0.0, 1.0});
    engine.send_event(StructuralEvent{StructArbType::DISPERSION, "SPX_VOL", "BASKET_VOL", 12.0, 18.0, 0.0, 2.0});
    engine.send_event(StructuralEvent{StructArbType::SHARE_CLASS, "GOOG", "GOOGL", 153.5, 150.0, 2.0, 3.0});
    engine.send_event(StructuralEvent{StructArbType::DUAL_LISTED, "UN_ADR", "UN_LSE", 50.0, 38.0, 1.25, 4.0});
    engine.send_event(StructuralEvent{StructArbType::ODD_LOT, "AAPL", "AAPL_NBBO", 99.0, 100.0, 45.0, 5.0});
    engine.send_event(StructuralEvent{StructArbType::DELTA_GAMMA, "SPY", "", 400.0, 0.0, 15.0, 6.0});
    return {engine.get_total_equity(), engine.get_max_drawdown(), engine.get_trade_history().size()};
}

Golden RunMacroEvents() {
    Backtester engine(100000.0, "GLOBAL_MACRO", 1.0);
    engine.send_event(MacroEvent{MacroEventType::YIELD_CURVE, "US2Y", "US10Y", 4.50, 4.55, 2.0});
    engine.send_event(MacroEvent{MacroEventType::CALENDER_SPREAD, "CL_NEAR", "CL_FAR", 75.0, 82.0, 3.0});
    engine.send_event(MacroEvent{MacroEventType::FI_CARRY_TRADE, "JPY", "USD", 0.1, 5.0, 4.0});
    engine.send_event(MacroEvent{MacroEventType::COMMODITY_FX, "WTI_CRUDE", "USDCAD", 6.5, 0.0, 5.0});
    return {engine.get_total_equity(), engine.get_max_drawdown(), engine.get_trade_history().size()};
}

constexpr Golden kGoldenMeta{-100220.0, 0.0, 4};
constexpr Golden kGoldenStructural{99025.1873947, 0.0, 6};
constexpr Golden kGoldenMacro{-891727.85, 0.0, 5};

} // namespace

TEST(BacktesterCharacterization, MacdDeterministicRun) {
    PrintAndCheck("MACD", RunEngine("MACD"), kGoldenMacd);
}

TEST(BacktesterCharacterization, EmaDeterministicRun) {
    PrintAndCheck("EMA", RunEngine("EMA"), kGoldenEma);
}

TEST(BacktesterCharacterization, MetaEventsRun) {
    PrintAndCheck("META_BRAIN", RunMetaEvents(), kGoldenMeta);
}

TEST(BacktesterCharacterization, StructuralEventsRun) {
    PrintAndCheck("STRUCTURAL_ARB", RunStructuralEvents(), kGoldenStructural);
}

TEST(BacktesterCharacterization, MacroEventsRun) {
    PrintAndCheck("GLOBAL_MACRO", RunMacroEvents(), kGoldenMacro);
}
