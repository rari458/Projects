# CMakeLists.txt

cmake_minimum_required(VERSION 3.24)
project(FinancialEngine VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# Tests + benchmarks are dev-only. Wheel builds (scikit-build-core) set this OFF
# so they never fetch googletest/benchmark or build those targets.
option(FINANCIAL_OS_BUILD_TESTS "Build unit tests and benchmarks" ON)

if(FINANCIAL_OS_BUILD_TESTS)
    enable_testing()
endif()

include(FetchContent)

# --- Core dependencies (always needed: static lib + Python module) ---
FetchContent_Declare(
    fmt
    URL https://github.com/fmtlib/fmt/archive/10.2.1.zip
    DOWNLOAD_EXTRACT_TIMESTAMP TRUE
)
FetchContent_MakeAvailable(fmt)

FetchContent_Declare(
    pybind11
    URL https://github.com/pybind/pybind11/archive/refs/tags/v2.11.1.zip
    DOWNLOAD_EXTRACT_TIMESTAMP TRUE
)

FetchContent_Declare(
    eigen
    URL https://gitlab.com/libeigen/eigen/-/archive/3.4.0/eigen-3.4.0.zip
    DOWNLOAD_EXTRACT_TIMESTAMP TRUE
)
set(BUILD_TESTING OFF CACHE BOOL "" FORCE)
set(EIGEN_BUILD DOC OFF)
FetchContent_MakeAvailable(eigen)

set(PYBIND11_FINDPYTHON ON)
FetchContent_MakeAvailable(pybind11)

# --- Dev-only dependencies (unit tests + benchmarks) ---
if(FINANCIAL_OS_BUILD_TESTS)
    FetchContent_Declare(
        googletest
        URL https://github.com/google/googletest/archive/refs/tags/v1.14.0.zip
        DOWNLOAD_EXTRACT_TIMESTAMP TRUE
    )
    set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
    FetchContent_MakeAvailable(googletest)

    FetchContent_Declare(
        benchmark
        URL https://github.com/google/benchmark/archive/refs/tags/v1.8.3.zip
        DOWNLOAD_EXTRACT_TIMESTAMP TRUE
    )
    set(BENCHMARK_ENABLE_TESTING OFF CACHE BOOL "" FORCE)
    set(BENCHMARK_ENABLE_GTEST_TESTS OFF CACHE BOOL "" FORCE)
    set(BENCHMARK_ENABLE_WERROR OFF CACHE BOOL "" FORCE)
    FetchContent_MakeAvailable(benchmark)
endif()

add_subdirectory(src)

if(FINANCIAL_OS_BUILD_TESTS)
    add_subdirectory(tests)
    add_subdirectory(benchmarks)
endif()