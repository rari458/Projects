#include "aegis/gateway/binance_gateway.hpp"
#include "pipeline/kafka_producer.hpp"
#include <iostream>

int main() {
    std::cout << "[Aegis] Starting Trading Engine...\n";

    aegis::gateway::BinanceGateway gateway;
    aegis::pipeline::KafkaProducer producer("localhost:9092", "binance_l2_depth");

    gateway.set_message_handler([&producer](const aegis::gateway::MessagePayload& payload) {
        producer.produce(payload.data);
    });

    gateway.connect("stream.binance.com");
    gateway.subscribe("btcusdt@depth10@100ms");

    gateway.run();

    return 0;
}