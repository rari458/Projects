# ../gateway/CMakeLists.txt
project(aegis_gateway)

find_package(Boost REQUIRED COMPONENTS system thread)
find_package(OpenSSL REQUIRED)

# Changed from INTERFACE to STATIC and added the .cpp file
add_library(gateway STATIC 
    src/binance_gateway.cpp
)

# Changed INTERFACE to PUBLIC so dependents inherit the includes
target_include_directories(gateway PUBLIC 
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)

target_link_libraries(gateway PUBLIC 
    Boost::system 
    Boost::thread 
    OpenSSL::SSL 
    OpenSSL::Crypto
)