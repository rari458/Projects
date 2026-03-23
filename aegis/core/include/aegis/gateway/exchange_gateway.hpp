#pragma once

#include <cstddef>
#include <span>
#include <string_view>
#include <functional>
#include <cstdint>

namespace aegis::gateway {

struct MessagePayload {
    std::span<const std::byte> data;
    uint64_t receive_timestamp_ns; 
};

using MessageHandler = std::function<void(const MessagePayload&)>;

class ExchangeGateway {
public:
    virtual ~ExchangeGateway() = default;

    virtual void connect(std::string_view uri) = 0;
    virtual void disconnect() = 0;
    virtual void subscribe(std::string_view stream_name) = 0;

    virtual void set_message_handler(MessageHandler handler) = 0;
    virtual void run() = 0;
};

} // namespace aegis::gateway