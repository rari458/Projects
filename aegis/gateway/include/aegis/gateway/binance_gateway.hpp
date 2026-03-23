#pragma once

#include "aegis/gateway/exchange_gateway.hpp"
#include <memory>
#include <string_view>

namespace aegis::gateway {

class BinanceGateway : public ExchangeGateway {
public:
    BinanceGateway();
    ~BinanceGateway() override;

    void connect(std::string_view uri) override;
    void disconnect() override;
    void subscribe(std::string_view stream_name) override;
    void set_message_handler(MessageHandler handler) override;
    void run() override;

private:
    struct Impl;
    std::unique_ptr<Impl> pimpl_;
};

} // namespace aegis::gateway
