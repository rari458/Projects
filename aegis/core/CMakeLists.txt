# core/CMakeLists.txt
project(aegis_core)

add_executable(aegis_engine src/main.cpp)

target_link_libraries(aegis_engine PRIVATE gateway pipeline)
target_include_directories(aegis_engine PRIVATE include)
