#include "dominion/bus.hpp"
#include <nlohmann/json.hpp>
#include <httplib.h>
#include <chrono>
#include <iostream>
#include <iomanip>
#include <sstream>

using json = nlohmann::json;

namespace dominion {

namespace {
    std::string iso8601_now() {
        auto now = std::chrono::system_clock::now();
        auto now_t = std::chrono::system_clock::to_time_t(now);
        auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
            now.time_since_epoch()) % 1000;

        char buf[64];
        std::strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%S", std::gmtime(&now_t));
        std::snprintf(buf + std::strlen(buf), sizeof(buf) - std::strlen(buf), ".%03ldZ", ms.count());
        return buf;
    }
}

// HTTP-only implementation (WebSocket requires boost, deferred)
BusClient::BusClient(const std::string& url) : url_(url) {}
BusClient::~BusClient() {}

bool BusClient::connect() {
    connected_ = true;
    return true;
}

void BusClient::disconnect() {
    connected_ = false;
}

bool BusClient::send(const std::string& topic, const std::string& payload_json) {
    if (!connected_) return false;

    try {
        // Extract host from ws:// URL (convert to http://)
        std::string http_url = url_;
        if (http_url.find("ws://") == 0) {
            http_url = "http://" + http_url.substr(5);
        }

        size_t scheme_end = http_url.find("://");
        size_t host_start = scheme_end + 3;
        size_t path_start = http_url.find("/", host_start);

        std::string host = http_url.substr(host_start, path_start - host_start);
        std::string path = (path_start != std::string::npos) ? http_url.substr(path_start) : "/bus";

        httplib::Client cli(("http://" + host).c_str());
        cli.set_read_timeout(5);

        json msg = {
            {"topic", topic},
            {"payload", json::parse(payload_json)},
            {"timestamp", iso8601_now()}
        };

        auto res = cli.Post(path.c_str(), msg.dump(), "application/json");
        return res && (res->status == 200 || res->status == 202);

    } catch (const std::exception& e) {
        std::cerr << "Bus send error: " << e.what() << std::endl;
        return false;
    }
}

void BusClient::subscribe(MessageHandler handler) {
    handler_ = handler;
    // HTTP polling not implemented; requires separate thread
}

void BusClient::run_async() {
    // Stub: WebSocket event loop replaced with HTTP POST-only
}

bool BusClient::is_connected() const {
    return connected_;
}

// Publisher implementation
BusPublisher::BusPublisher(const std::string& url) : url_(url) {}

bool BusPublisher::publish(const std::string& topic, const std::string& payload_json) {
    try {
        BusClient client(url_);
        client.connect();
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
        return client.connect();
    } catch (...) {
        return false;
    }
}

} // namespace dominion
