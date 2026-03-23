# CMakeLists.txt (Root)
cmake_minimum_required(VERSION 3.20)
project(Aegis VERSION 1.0.0 LANGUAGES CXX)

# Use Modern C++ Standards
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Compiler optimizations for low-latency
set(CMAKE_CXX_FLAGS_RELEASE "-O3 -march=native -flto -DNDEBUG")

# Global include directories
include_directories(${CMAKE_SOURCE_DIR}/core/include)
include_directories(${CMAKE_SOURCE_DIR}/pipeline/include)

# Add subdirectories for modular build
add_subdirectory(core)
add_subdirectory(pipeline)
add_subdirectory(gateway)

# Optional: Build tests if requested
option(AEGIS_BUILD_TESTS "Build unit tests" ON)
if(AEGIS_BUILD_TESTS)
    enable_testing()
    add_subdirectory(tests)
endif()