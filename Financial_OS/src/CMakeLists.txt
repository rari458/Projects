# src/CMakeLists.txt

find_package(Eigen3 REQUIRED)

set(SOURCES
    Optimizer.cpp
    Backtester.cpp
    Analytics.cpp
    Payoff.cpp
    SimpleMC.cpp
    Parameters.cpp
    VanillaOption.cpp
    MCStatistics.cpp
    ConvergenceTable.cpp
    Random.cpp
    AntiThetic.cpp
    PathDependent.cpp
    PathDependentAsian.cpp
    ExoticBSEngine.cpp
    PayoffFactory.cpp
    PayoffRegistration.cpp
	BlackScholesFormulas.cpp
	BinomialTree.cpp
    PairSelector.cpp
    RegimeDetector.cpp
    PCAArbitrage.cpp
    OrderBook.cpp
    StrategyFactory.cpp
)

add_library(FinancialEngine STATIC ${SOURCES})

set_target_properties(FinancialEngine PROPERTIES POSITION_INDEPENDENT_CODE ON)

target_link_libraries(FinancialEngine PUBLIC fmt::fmt Eigen3::Eigen)
target_include_directories(FinancialEngine PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/../include)

target_include_directories(FinancialEngine SYSTEM PRIVATE ${bs_thread_pool_SOURCE_DIR}/include)

if(MSVC)
    target_compile_options(FinancialEngine PRIVATE /W4 /WX)
else()
    target_compile_options(FinancialEngine PRIVATE -Wall -Wextra -Werror -flto=auto)
    # INTERFACE, not PRIVATE: a static library is never linked itself, so a private
    # link option reached no binary. Every program linking FinancialEngine has to
    # link its LTO objects with -flto; gcc's linker plugin coped without the flag,
    # clang's does not (ld: "file format not recognized").
    target_link_options(FinancialEngine INTERFACE -flto=auto)
endif()

add_executable(FinancialOS main.cpp PayoffRegistration.cpp StrategyRegistration.cpp)
target_link_libraries(FinancialOS PRIVATE FinancialEngine fmt::fmt)

pybind11_add_module(FinancialEnginePy Bindings.cpp PayoffRegistration.cpp StrategyRegistration.cpp)
target_link_libraries(FinancialEnginePy PRIVATE FinancialEngine)
set_target_properties(FinancialEnginePy PROPERTIES OUTPUT_NAME "FinancialEngine")

install(TARGETS FinancialEnginePy LIBRARY DESTINATION . COMPONENT python)

add_library(financial_engine_c SHARED
    EngineCApi.cpp
    StrategyRegistration.cpp
    PayoffRegistration.cpp
)
target_link_libraries(financial_engine_c PRIVATE FinancialEngine fmt::fmt)
if(MSVC)
    target_compile_options(financial_engine_c PRIVATE /W4 /WX)
else()
    target_compile_options(financial_engine_c PRIVATE -Wall -Wextra -Werror)
endif()