// src/StrategyRegistration.cpp

#include <memory>

#include "../include/Strategy.h"
#include "../include/StrategyFactory.h"

namespace {

class StrategyRegistrar {
public:
    StrategyRegistrar() {
        auto& f = StrategyFactory::Instance();

        // --- Classic technical / statistical strategies --
        f.RegisterStrategy("EMA", [] { return std::make_unique<EMAStrategy>(); });
        f.RegisterStrategy("RSI", [] { return std::make_unique<RSIStrategy>(); });
        f.RegisterStrategy("MACD", [] { return std::make_unique<MACDStrategy>(); });
        f.RegisterStrategy("BB", [] { return std::make_unique<BollingerStrategy>(); });
        f.RegisterStrategy("VOL", [] { return std::make_unique<VolatilityStrategy>(); });
        f.RegisterStrategy("OU", [] { return std::make_unique<OUStrategy>(); });

        // --- Pairs / stat-arb ---
        f.RegisterStrategy("PAIRS", [] { return std::make_unique<KalmanPairsStrategy>("KO", "PEP"); });
        f.RegisterStrategy("PCA", [] { return std::make_unique<PCAStatArbStrategy>(60, 2.0); });

        // --- Vol / options / market making ---
        f.RegisterStrategy("GAMMA", [] { return std::make_unique<GammaScalpingStrategy>(1000.0, 100.0, 0.20, 5.0); });
        f.RegisterStrategy("MM", [] { return std::make_unique<MarketMakerStrategy>(0.1, 0.2, 1.5); });
        f.RegisterStrategy("VRP", [] { return std::make_unique<VRPHarvestingStrategy>(100.0, 30.0 / 252.0, 0.05); });
        f.RegisterStrategy("AVELLANEDA", [] { return std::make_unique<AvellanedaStoikovStrategy>(0.1, 0.2, 1.5, 1.0); });

        // --- Execution algos ---
        f.RegisterStrategy("VWAP", [] { return std::make_unique<VWAPExecutionStrategy>(10000.0, 500.0, 200.0); });
        f.RegisterStrategy("TWAP", [] { return std::make_unique<TWAPExecutionStrategy>(10000.0, 200.0); });
        f.RegisterStrategy("POV", [] { return std::make_unique<POVExecutionStrategy>(10000.0, 0.05); });
        f.RegisterStrategy("ICEBERG", [] { return std::make_unique<IcebergExecutionStrategy>(10000.0, 500.0); });
        f.RegisterStrategy("SNIPER", [] { return std::make_unique<SniperExecutionStrategy>(10000.0, 99.50); });

        // --- Multi-strategy "suites" ---
        f.RegisterStrategy("EVENT_DRIVEN", [] {return std::make_unique<EventDrivenSuite>(); });
        f.RegisterStrategy("MICROSTRUCTURE", [] {return std::make_unique<AdvancedMicrostructureSuite>(); });
        f.RegisterStrategy("CRYPTO_DEFI", [] { return std::make_unique<CryptoDeFiSuite>(); });
        f.RegisterStrategy("ALT_DATA", [] { return std::make_unique<AlternativeDataSuite>(); });
        f.RegisterStrategy("DOWNSIDE_SQUEEZE", [] { return std::make_unique<AdvancedDownsideSuite>(); });
        f.RegisterStrategy("GLOBAL_MACRO", [] { return std::make_unique<GlobalMacroSuite>(); });
        f.RegisterStrategy("AI_BHV", [] {return std::make_unique<AIBehavioralSuite>(); });
        f.RegisterStrategy("GRAND_FINALE", [] { return std::make_unique<GrandFinaleSuite>(); });
        f.RegisterStrategy("L3_EXECUTION", [] { return std::make_unique<L3ExecutionSuite>(); });
        f.RegisterStrategy("STRUCTURAL_ARB", [] { return std::make_unique<StructuralArbSuite>(); });
        f.RegisterStrategy("DEEP_CYCLE", [] { return std::make_unique<DeepCryptoCycleSuite>(); });
        f.RegisterStrategy("META_BRAIN", [] { return std::make_unique<MetaBrainSuite>(); });
    }
};

const StrategyRegistrar regisTrar;

} // namespace
