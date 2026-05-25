#pragma once

#include <functional>
#include <memory>
#include <string>
#include <thread>
#include <atomic>
#include <mutex>
#include <queue>

namespace dominion {

namespace topics {
    constexpr const char* PIPELINE_RUN_COMPLETE = "pipeline.run.complete";
    constexpr const char* PIPELINE_ANOMALY = "pipeline.anomaly";
    constexpr const char* PIPELINE_REGIME_CHANGE = "pipeline.regime_change";
    constexpr const char* PIPELINE_SOURCE_HEALTH = "pipeline.source_health";
    constexpr const char* CAUSAL_DAG_UPDATED = "causal.dag_updated";
    constexpr const char* RESERVOIR_PREDICTION = "reservoir.prediction";
    constexpr const char* GRAPH_EMBEDDING_UPDATED = "graph.embedding_updated";
}

struct BusMessage {
    std::string topic;
    std::string payload_json;
    std::string timestamp;
};

using MessageHandler = std::function<void(const BusMessage&)>;

class BusClient {
public:
    explicit BusClient(const std::string& url = "ws://127.0.0.1:7474/bus");
    ~BusClient();

    bool connect();
    void disconnect();
    bool send(const std::string& topic, const std::string& payload_json);
    void subscribe(MessageHandler handler);
    void run_async();
    bool is_connected() const;

private:
    void reconnect_loop();

    std::string url_;
    std::atomic<bool> connected_{false};
    std::atomic<bool> running_{false};
    MessageHandler handler_;
    std::unique_ptr<std::thread> recv_thread_;
    std::mutex send_mutex_;
    double reconnect_delay_ = 1.0;
    static constexpr double max_reconnect_delay_ = 30.0;
};

class BusPublisher {
public:
    explicit BusPublisher(const std::string& url = "ws://127.0.0.1:7474/bus");

    bool publish_pipeline_complete(const std::string& run_id, int sources_fetched, int features_computed);
    bool publish_anomaly(const std::string& timestamp, const std::string& type,
                         const std::string& severity, const std::string& source);
    bool publish_regime_change(const std::string& timestamp,
                               const std::string& old_regime, const std::string& new_regime);
    bool publish_dag_updated(const std::string& run_id, int n_edges);
    bool test_connection();

private:
    bool publish(const std::string& topic, const std::string& payload_json);
    std::string url_;
};

} // namespace dominion
