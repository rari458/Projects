cmake_minimum_required(VERSION 3.20)
project(hybrid_backtester CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

find_package(Threads REQUIRED)

set(BENCH_FLAGS -Wall -Wextra -Werror -O2 -march=native -fno-omit-frame-pointer)

add_executable(noise_floor noise_floor.cpp)
target_compile_options(noise_floor PRIVATE ${BENCH_FLAGS})
target_link_libraries(noise_floor PRIVATE Threads::Threads)

add_executable(ring_bench ring_bench.cpp)
target_compile_options(ring_bench PRIVATE ${BENCH_FLAGS})
target_link_libraries(ring_bench PRIVATE Threads::Threads)

add_executable(layout_dump layout_dump.cpp)
target_compile_options(layout_dump PRIVATE ${BENCH_FLAGS})