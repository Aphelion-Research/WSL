#pragma once

#include "dominion/types.hpp"

#include <memory>
#include <string>
#include <vector>
#include <unordered_map>

namespace dominion {

class Storage {
public:
    explicit Storage(const std::string& db_path);
    ~Storage();

    void init_schema();

    // Pipeline runs
    void log_run_start(PipelineRun& run);
    void log_run_complete(const PipelineRun& run);
    PipelineRun get_last_run();

    // Raw data
    void store_bars(const std::vector<Bar>& bars);
    void store_macro(const std::vector<MacroData>& data);
    void store_cot(const std::vector<COTData>& data);

    // Fused data
    void store_fused_bars(const std::vector<FusedBar>& bars);
    std::vector<FusedBar> load_fused_bars(int limit = 1000);

    // Ticks
    void store_ticks(const std::vector<Tick>& ticks);
    std::vector<Tick> load_ticks(int limit = 1000);

    // Features
    void store_features(const std::vector<Feature>& features);
    std::vector<Feature> load_features(const std::string& name = "", int limit = 1000);
    std::unordered_map<std::string, double> get_feature_importance(int top_n = 50);

    // Regimes
    void store_regimes(const std::vector<RegimeLabel>& regimes);
    std::vector<RegimeLabel> load_regimes(int limit = 100);

    // Health
    void store_source_health(const std::vector<SourceHealth>& health);
    std::vector<SourceHealth> load_source_health();

    // Anomalies
    void log_anomaly(const Anomaly& anomaly);
    std::vector<Anomaly> get_recent_anomalies(int hours = 24);

    // Intelligence reports
    void store_report(const std::string& report_date, const std::string& report_text, bool ragd_stored);
    std::string get_latest_report();

private:
    class Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace dominion
