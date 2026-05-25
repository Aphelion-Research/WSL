#pragma once

#include <chrono>
#include <cstdint>
#include <optional>
#include <string>
#include <vector>
#include <unordered_map>

namespace dominion {

using Timestamp = std::chrono::system_clock::time_point;
using Duration = std::chrono::milliseconds;

struct Tick {
    int64_t time_msc;
    double bid;
    double ask;
    double mid;
    double spread;
    int32_t flags;
    int64_t volume;
    int64_t volume_real;
    Timestamp collected_at;
};

struct Bar {
    Timestamp timestamp;
    double open;
    double high;
    double low;
    double close;
    int64_t volume;
    int64_t tick_volume;
    double spread;
    std::string source;
    double quality_score = 1.0;
};

struct FusedBar {
    Timestamp timestamp;
    double open;
    double high;
    double low;
    double close;
    int64_t volume;
    double fused_price;
    double fused_confidence;
    std::unordered_map<std::string, double> source_weights;
    bool anomaly_flag = false;
    std::string regime;
};

struct MacroData {
    std::string series_id;
    Timestamp timestamp;
    double value;
    std::string series_name;
};

struct COTData {
    Timestamp report_date;
    int64_t commercial_long;
    int64_t commercial_short;
    int64_t noncommercial_long;
    int64_t noncommercial_short;
    int64_t open_interest;
    int64_t net_commercial;
    double speculator_sentiment;
};

struct Feature {
    Timestamp timestamp;
    std::string name;
    double value;
    std::string version = "1.0";
    std::optional<double> ic_252;
};

struct RegimeLabel {
    Timestamp timestamp;
    std::string macro_regime;
    std::string structural_regime;
    std::string tactical_regime;
    std::string micro_regime;
    double confidence;
};

struct SourceHealth {
    std::string source;
    Timestamp last_fetch;
    std::string status;
    double latency_ms;
    int error_count;
    double trust_score;
};

struct Anomaly {
    Timestamp timestamp;
    std::string type;
    std::string description;
    std::string severity;
    std::string source;
    double value;
};

struct PipelineRun {
    std::string run_id;
    Timestamp started_at;
    std::optional<Timestamp> completed_at;
    std::string status;
    int sources_fetched = 0;
    int features_computed = 0;
    std::vector<std::string> errors;
};

template <typename T>
using TimeSeries = std::vector<T>;

using PriceVec = std::vector<double>;
using FeatureVec = std::vector<double>;
using FeatureMap = std::unordered_map<std::string, FeatureVec>;

} // namespace dominion
