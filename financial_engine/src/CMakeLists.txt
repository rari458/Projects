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
)

add_library(FinancialEngine STATIC ${SOURCES})

set_target_properties(FinancialEngine PROPERTIES POSITION_INDEPENDENT_CODE ON)

target_link_libraries(FinancialEngine PUBLIC fmt::fmt Eigen3::Eigen)
target_include_directories(FinancialEngine PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/../include)

if(MSVC)
    target_compile_options(FinancialEngine PRIVATE /W4 /WX)
else()
    target_compile_options(FinancialEngine PRIVATE -Wall -Wextra -Werror -flto=auto)
    target_link_options(FinancialEngine PRIVATE -flto=auto)
endif()

add_executable(FinancialOS main.cpp PayoffRegistration.cpp)
target_link_libraries(FinancialOS PRIVATE FinancialEngine fmt::fmt)

pybind11_add_module(FinancialEnginePy Bindings.cpp PayoffRegistration.cpp)
target_link_libraries(FinancialEnginePy PRIVATE FinancialEngine)
set_target_properties(FinancialEnginePy PROPERTIES OUTPUT_NAME "FinancialEngine")