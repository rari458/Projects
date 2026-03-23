#pragma once

#include <string>
#include <memory>
#include <span>
#include <cstddef>

namespace aegis::pipeline {

class KafkaProducer {
public:
    KafkaProducer(const std::string& brokers, const std::string& topic);
    ~KafkaProducer();

    void produce(std::span<const std::byte> payload);
    void flush(int timeout_ms = 10000);

private:
    struct Impl;
    std::unique_ptr<Impl> pimpl_;
};

} // namespace aegis::pipeline