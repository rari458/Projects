# pipeline/CMakeLists.txt
project(aegis_pipeline)

add_library(pipeline STATIC src/kafka_producer.cpp)

target_include_directories(pipeline PUBLIC
	$<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
	$<INSTALL_INTERFACE:include>
)

target_link_libraries(pipeline PUBLIC rdkafka++)
