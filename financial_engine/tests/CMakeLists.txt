include(GoogleTest)

add_executable(UnitTests
    PayoffTest.cpp
    SimpleMCTest.cpp
    ConvergenceTest.cpp
    AntiTheticTest.cpp
    ExoticEngineTest.cpp
    FactoryTest.cpp
    ../src/PayoffRegistration.cpp
	SolverTest.cpp
	TreeTest.cpp
	GreeksTest.cpp
)

target_link_libraries(UnitTests
    PRIVATE
    ${PROJECT_NAME}
    GTest::gtest_main
    fmt::fmt
)

gtest_discover_tests(UnitTests)
