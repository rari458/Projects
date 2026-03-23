#include "aegis/gateway/binance_gateway.hpp"

#include <boost/asio.hpp>
#include <boost/asio/ssl.hpp>
#include <boost/beast.hpp>
#include <boost/beast/ssl.hpp>
#include <chrono>
#include <iostream>

namespace net = boost::asio;
namespace ssl = boost::asio::ssl;
namespace beast = boost::beast;
namespace websocket = beast::websocket;
using tcp = net::ip::tcp;

namespace aegis::gateway {

struct BinanceGateway::Impl {
    net::io_context ioc;
    ssl::context ctx{ssl::context::tlsv12_client};
    tcp::resolver resolver{ioc};
    std::unique_ptr<websocket::stream<beast::ssl_stream<tcp::socket>>> ws;
    beast::flat_buffer buffer;
    MessageHandler handler;

    std::string host;
    std::string port;

    Impl() {
        ctx.set_default_verify_paths();
        ctx.set_verify_mode(ssl::verify_peer);
    }

    void do_read() {
        ws->async_read(buffer, [this](beast::error_code ec, std::size_t bytes_transferred) {
            if (ec) {
                std::cerr << "[Gateway] Async read error: " << ec.message() << "\n";
                return;
            }

            if (handler) {
                auto data = buffer.data();
                std::span<const std::byte> payload(
                    static_cast<const std::byte*>(data.data()),
                    buffer.size()
                );

                uint64_t ts = std::chrono::duration_cast<std::chrono::nanoseconds>(
                    std::chrono::system_clock::now().time_since_epoch()
                ).count();

                handler({payload, ts});
            }

            buffer.consume(buffer.size());
            do_read();
        });
    }
};

BinanceGateway::BinanceGateway() : pimpl_(std::make_unique<Impl>()) {}
BinanceGateway::~BinanceGateway() = default;

void BinanceGateway::connect(std::string_view uri) {
    pimpl_->host = std::string(uri);
    pimpl_->port = "443";

    try {
        auto const results = pimpl_->resolver.resolve(pimpl_->host, pimpl_->port);

        pimpl_->ws = std::make_unique<websocket::stream<beast::ssl_stream<tcp::socket>>>(
            net::make_strand(pimpl_->ioc), pimpl_->ctx
        );

        if(!SSL_set_tlsext_host_name(pimpl_->ws->next_layer().native_handle(), pimpl_->host.c_str())) {
            throw beast::system_error(
                beast::error_code(static_cast<int>(::ERR_get_error()), net::error::get_ssl_category()),
                "Failed to set SNI Hostname"
            );
        }

        auto ep = net::connect(pimpl_->ws->next_layer().next_layer(), results);
        pimpl_->ws->next_layer().handshake(ssl::stream_base::client);
        pimpl_->ws->handshake(pimpl_->host, "/ws");

        std::cout << "[Gateway] Connected to " << pimpl_->host << "\n";
        pimpl_->do_read();

    } catch (std::exception const& e) {
        std::cerr << "[Gateway] Connection Error: " << e.what() << "\n";
    }
}

void BinanceGateway::disconnect() {
    if (pimpl_->ws) {
        beast::error_code ec;
        pimpl_->ws->close(websocket::close_code::normal, ec);
    }
}

void BinanceGateway::subscribe(std::string_view stream_name) {
    if (!pimpl_->ws) return;
    std::string payload = R"({"method": "SUBSCRIBE", "params": [")" + std::string(stream_name) + R"("], "id": 1})";
    pimpl_->ws->write(net::buffer(payload));
    std::cout << "[Gateway] Subscribed to " << stream_name << "\n";
}

void BinanceGateway::set_message_handler(MessageHandler handler) {
    pimpl_->handler = std::move(handler);
}

void BinanceGateway::run() {
    pimpl_->ioc.run();
}

} // namespace aegis::gateway