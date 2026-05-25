#pragma once

#include "dominion/types.hpp"

#include <string>
#include <unordered_map>
#include <vector>

namespace dominion {

struct StalenessStatus {
    std::string source;
    Timestamp last_fetch;
    double age_seconds;
    double threshold_seconds;
    bool is_stale;
};

struct GapInfo {
    Timestamp start;
    Timestamp end;
    int missing_bars;
};

struct DriftResult {
    std::string feature_name;
    double kl_divergence;
    bool is_drifting;
};

struct HealthSummary {
    std::unordered_map<std::string, StalenessStatus> staleness;
    std::vector<GapInfo> gaps;
    std::vector<Anomaly> recent_anomalies;
    double gold_dxy_correlation;
    bool gold_dxy_inverted;
    std::vector<DriftResult> drifts;
    bool overall_healthy;
};

class PipelineMonitor {
public:
    explicit PipelineMonitor(const std::string& db_path);

    std::unordered_map<std::string, StalenessStatus> check_staleness(
        const std::unordered_map<std::string, int>& thresholds_hours);

    std::vector<GapInfo> detect_gaps(const std::string& table = "gold_master",
                                      int max_gap_bars = 5);

    int fill_small_gaps(const std::string& table = "gold_master",
                        int max_gap_bars = 5);

    DriftResult detect_drift(const std::string& feature_name, int window = 252);

    std::pair<bool, double> monitor_gold_dxy_correlation(int window = 20);

    HealthSummary get_health_summary(
        const std::unordered_map<std::string, int>& thresholds);

private:
    std::string db_path_;
};

class AnomalyDetector {
public:
    explicit AnomalyDetector(double z_flag = 3.0, double z_quarantine = 5.0);

    struct PriceAnomaly {
        bool flagged;
        bool quarantined;
        double z_score;
    };

    PriceAnomaly detect_price_anomaly(double price, double mean, double std);
    bool detect_volume_anomaly(double volume, double mean, double std, double threshold = 5.0);
    bool detect_source_divergence(const std::unordered_map<std::string, double>& prices,
                                   double sigma_threshold = 2.0);

private:
    double z_flag_;
    double z_quarantine_;
};

class ReportGenerator {
public:
    ReportGenerator(const std::string& db_path, const std::string& ragd_url,
                    const std::string& reports_dir);

    std::string generate(const std::string& run_id);
    bool send_to_ragd(const std::string& report_text, const std::string& report_date);

private:
    std::string db_path_;
    std::string ragd_url_;
    std::string reports_dir_;
};

} // namespace dominion
