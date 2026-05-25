#include "dominion/bus.hpp"
#include <nlohmann/json.hpp>
#include <websocketpp/config/asio_client.hpp>
#include <websocketpp/client.hpp>
#include <chrono>
#include <iostream>

using json = nlohmann::json;
using websocketpp::connection_hdl;
using websocketpp::lib::placeholders::_1;
using websocketpp::lib::placeholders::_2;
using websocketpp::lib::bind;

namespace dominion {

namespace {
    using Client = websocketpp::client<websocketpp::config::asio_tls_client>;
    using MessagePtr = Client::message_ptr;
    using ContextPtr = websocketpp::lib::shared_ptr<websocketpp::lib::asio::ssl::context>;

    ContextPtr on_tls_init() {
        auto ctx = websocketpp::lib::make_shared<websocketpp::lib::asio::ssl::context>(
            websocketpp::lib::asio::ssl::context::tlsv12_client);
        ctx->set_options(websocketpp::lib::asio::ssl::context::default_workarounds |
                        websocketpp::lib::asio::ssl::context::no_sslv2 |
                        websocketpp::lib::asio::ssl::context::single_dh_use);
        return ctx;
    }

    std::string iso8601_now() {
        auto now = std::chrono::system_clock::now();
        auto now_t = std::chrono::system_clock::to_time_t(now);
        auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
            now.time_since_epoch()) % 1000;

        char buf[64];
        std::strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%S", std::gmtime(&now_t));
        snprintf(buf + strlen(buf), sizeof(buf) - strlen(buf), ".%03ldZ", ms.count());
        return buf;
    }
}

struct BusClient::Impl {
    Client ws_client;
    connection_hdl hdl;
    MessageHandler handler;
    std::string url;
    std::atomic<bool> connected{false};
    std::atomic<bool> running{false};
    double reconnect_delay = 1.0;

    void on_message(connection_hdl, MessagePtr msg) {
        if (!handler) return;
        try {
            auto j = json::parse(msg->get_payload());
            BusMessage bm{
                j.value("topic", ""),
                j.value("payload", json::object()).dump(),
                j.value("timestamp", "")
            };
            handler(bm);
        } catch (const std::exception& e) {
            std::cerr << "Bus message parse error: " << e.what() << std::endl;
        }
    }

    void on_open(connection_hdl h) {
        hdl = h;
        connected = true;
        reconnect_delay = 1.0;
        std::cout << "Bus connected: " << url << std::endl;
    }

    void on_close(connection_hdl) {
        connected = false;
        std::cout << "Bus disconnected" << std::endl;
    }

    void on_fail(connection_hdl) {
        connected = false;
        std::cerr << "Bus connection failed" << std::endl;
    }
};

BusClient::BusClient(const std::string& url)
    : url_(url), impl_(std::make_unique<Impl>()) {
    impl_->url = url;
    impl_->ws_client.init_asio();
    impl_->ws_client.set_tls_init_handler(bind(&on_tls_init));
    impl_->ws_client.set_message_handler(
        bind(&BusClient::Impl::on_message, impl_.get(), ::_1, ::_2));
    impl_->ws_client.set_open_handler(
        bind(&BusClient::Impl::on_open, impl_.get(), ::_1));
    impl_->ws_client.set_close_handler(
        bind(&BusClient::Impl::on_close, impl_.get(), ::_1));
    impl_->ws_client.set_fail_handler(
        bind(&BusClient::Impl::on_fail, impl_.get(), ::_1));
}

BusClient::~BusClient() {
    disconnect();
}

bool BusClient::connect() {
    try {
        websocketpp::lib::error_code ec;
        auto con = impl_->ws_client.get_connection(url_, ec);
        if (ec) {
            std::cerr << "Bus connection error: " << ec.message() << std::endl;
            return false;
        }
        impl_->ws_client.connect(con);
        running_ = true;
        return true;
    } catch (const std::exception& e) {
        std::cerr << "Bus connect exception: " << e.what() << std::endl;
        return false;
    }
}

void BusClient::disconnect() {
    running_ = false;
    if (connected_) {
        try {
            impl_->ws_client.close(impl_->hdl, websocketpp::close::status::normal, "");
        } catch (...) {}
    }
    impl_->ws_client.stop();
}

bool BusClient::send(const std::string& topic, const std::string& payload_json) {
    if (!connected_) return false;

    try {
        json msg = {
            {"topic", topic},
            {"payload", json::parse(payload_json)},
            {"timestamp", iso8601_now()}
        };

        websocketpp::lib::error_code ec;
        impl_->ws_client.send(impl_->hdl, msg.dump(), websocketpp::frame::opcode::text, ec);
        if (ec) {
            std::cerr << "Bus send error: " << ec.message() << std::endl;
            running_ = false;
            return false;
        }
        return true;
    } catch (const std::exception& e) {
        std::cerr << "Bus send exception: " << e.what() << std::endl;
        return false;
    }
}

void BusClient::subscribe(MessageHandler handler) {
    impl_->handler = handler;
}

void BusClient::run_async() {
    recv_thread_ = std::make_unique<std::thread>([this]() {
        while (running_) {
            try {
                if (!connected_) {
                    std::this_thread::sleep_for(
                        std::chrono::milliseconds(static_cast<int>(reconnect_delay_ * 1000)));
                    reconnect_delay_ = std::min(max_reconnect_delay_, reconnect_delay_ * 2.0);
                    if (connect()) {
                        impl_->ws_client.run();
                    }
                } else {
                    impl_->ws_client.run();
                }
            } catch (const std::exception& e) {
                std::cerr << "Bus thread error: " << e.what() << std::endl;
                connected_ = false;
            }
        }
    });
}

bool BusClient::is_connected() const {
    return connected_;
}

// Publisher implementation
BusPublisher::BusPublisher(const std::string& url) : url_(url) {}

bool BusPublisher::publish(const std::string& topic, const std::string& payload_json) {
    try {
        BusClient client(url_);
        if (!client.connect()) return false;
        bool result = client.send(topic, payload_json);
        client.disconnect();
        return result;
    } catch (const std::exception& e) {
        std::cerr << "Bus publish error: " << e.what() << std::endl;
        return false;
    }
}

bool BusPublisher::publish_pipeline_complete(const std::string& run_id,
                                              int sources_fetched,
                                              int features_computed) {
    json payload = {
        {"run_id", run_id},
        {"sources_fetched", sources_fetched},
        {"features_computed", features_computed}
    };
    return publish(topics::PIPELINE_RUN_COMPLETE, payload.dump());
}

bool BusPublisher::publish_anomaly(const std::string& timestamp,
                                    const std::string& type,
                                    const std::string& severity,
                                    const std::string& source) {
    json payload = {
        {"timestamp", timestamp},
        {"anomaly_type", type},
        {"severity", severity},
        {"source", source}
    };
    return publish(topics::PIPELINE_ANOMALY, payload.dump());
}

bool BusPublisher::publish_regime_change(const std::string& timestamp,
                                          const std::string& old_regime,
                                          const std::string& new_regime) {
    json payload = {
        {"timestamp", timestamp},
        {"old_regime", old_regime},
        {"new_regime", new_regime}
    };
    return publish(topics::PIPELINE_REGIME_CHANGE, payload.dump());
}

bool BusPublisher::publish_dag_updated(const std::string& run_id, int n_edges) {
    json payload = {
        {"run_id", run_id},
        {"n_edges", n_edges}
    };
    return publish(topics::CAUSAL_DAG_UPDATED, payload.dump());
}

bool BusPublisher::test_connection() {
    try {
        BusClient client(url_);
        bool result = client.connect();
        client.disconnect();
        return result;
    } catch (...) {
        return false;
    }
}

} // namespace dominion
