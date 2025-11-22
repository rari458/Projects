cmake_minimum_required(VERSION 3.15)
project(backtester LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} -O3 -march=native -ffast-math")
set(CMAKE_BUILD_TYPE Release)

set(QUANTSUITE_ROOT ${CMAKE_CURRENT_SOURCE_DIR}/../..)

add_library(common STATIC
	${QUANTSUITE_ROOT}/libs/common-cpp/src/csv.cpp
)

target_include_directories(common PUBLIC 
	${QUANTSUITE_ROOT}/libs/common-cpp/include
)

add_executable(backtester
	src/main.cpp
	src/metrics.cpp
	src/strategy.cpp
)

target_link_libraries(backtester PRIVATE common)
