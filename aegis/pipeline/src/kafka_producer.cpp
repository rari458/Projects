#include "pipeline/kafka_producer.hpp"
#include <librdkafka/rdkafkacpp.h>
#include <iostream>
#include <stdexcept>

namespace aegis::pipeline {

class DeliveryReportCb : public RdKafka::DeliveryReportCb {
public:
    void dr_cb(RdKafka::Message& message) override {
        if (message.err() != RdKafka::ERR_NO_ERROR) {
            std::cerr << "[Kafka] Message delivery failed: " << message.errstr() << "\n";
        }
    }
};

struct KafkaProducer::Impl {
    std::string topic_name;
    std::unique_ptr<RdKafka::Producer> producer;
    DeliveryReportCb dr_cb;

    Impl(const std::string& brokers, const std::string& topic) : topic_name(topic) {
        std::string errstr;
        std::unique_ptr<RdKafka::Conf> conf(RdKafka::Conf::create(RdKafka::Conf::CONF_GLOBAL));

        conf->set("bootstrap.servers", brokers, errstr);
        conf->set("dr_cb", &dr_cb, errstr);

        conf->set("linger.ms", "1", errstr);
        conf->set("batch.num.messages", "1000", errstr);

        producer.reset(RdKafka::Producer::create(conf.get(), errstr));
        if (!producer) {
            throw std::runtime_error("Failed to create Kafka producer: " + errstr);
        }
    }
};

KafkaProducer::KafkaProducer(const std::string& brokers, const std::string& topic)
    : pimpl_(std::make_unique<Impl>(brokers, topic)) {}

KafkaProducer::~KafkaProducer() {
    flush(10000);
}

void KafkaProducer::produce(std::span<const std::byte> payload) {
    if (!pimpl_->producer) return;

    RdKafka::ErrorCode err = pimpl_->producer->produce(
        pimpl_->topic_name,
        RdKafka::Topic::PARTITION_UA,
        RdKafka::Producer::RK_MSG_COPY,
        const_cast<void*>(static_cast<const void*>(payload.data())),
        payload.size(),
        nullptr, 0,
        0,
        nullptr
    );

    if (err != RdKafka::ERR_NO_ERROR) {
        std::cerr << "[Kafka] Produce failed: "<< RdKafka::err2str(err) << "\n";
    }

    pimpl_->producer->poll(0);
}

void KafkaProducer::flush(int timeout_ms) {
    if (pimpl_->producer) {
        pimpl_->producer->flush(timeout_ms);
    }
}

} // namespace aegis::pipeline