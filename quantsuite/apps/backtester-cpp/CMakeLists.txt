cmake_minimum_required(VERSION 3.15)
project(backtester LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_library(common STATIC
	../../libs/common-cpp/src/csv.cpp
)
target_include_directories(common PUBLIC ../../libs/common-cpp/include)

add_executable(backtester
	src/main.cpp
	src/metrics.hpp
	src/metrics.cpp
)
target_link_libraries(backtester PRIVATE common)
