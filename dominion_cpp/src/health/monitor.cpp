#include "dominion/health.hpp"
#include "dominion/sqlite3_wrapper.h"
#include <sstream>
#include <cmath>
#include <algorithm>

namespace dominion {

namespace {
    Timestamp parse_iso(const std::string& s) {
        std::tm tm = {};
        std::istringstream ss(s);
        ss >> std::get_time(&tm, "%Y-%m-%dT%H:%M:%SZ");
        return std::chrono::system_clock::from_time_t(std::mktime(&tm));
    }
}

PipelineMonitor::PipelineMonitor(const std::string& db_path) : db_path_(db_path) {}

std::unordered_map<std::string, StalenessStatus> PipelineMonitor::check_staleness(
    const std::unordered_map<std::string, int>& thresholds_hours
) {
    std::unordered_map<std::string, StalenessStatus> result;

    sqlite3* db;
    sqlite3_open(db_path_.c_str(), &db);

    const char* sql = "SELECT source, last_fetch FROM source_health";
    sqlite3_stmt* stmt;
    sqlite3_prepare_v2(db, sql, -1, &stmt, nullptr);

    auto now = std::chrono::system_clock::now();

    while (sqlite3_step(stmt) == SQLITE_ROW) {
        std::string source = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 0));
        std::string last_fetch_str = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 1));

        Timestamp last_fetch = parse_iso(last_fetch_str);
        auto age = std::chrono::duration_cast<std::chrono::seconds>(now - last_fetch);

        StalenessStatus status;
        status.source = source;
        status.last_fetch = last_fetch;
        status.age_seconds = age.count();
        status.threshold_seconds = (thresholds_hours.find(source) != thresholds_hours.end())
                                    ? thresholds_hours.at(source) * 3600
                                    : 86400;
        status.is_stale = age.count() > status.threshold_seconds;

        result[source] = status;
    }

    sqlite3_finalize(stmt);
    sqlite3_close(db);

    return result;
}

std::vector<GapInfo> PipelineMonitor::detect_gaps(const std::string& table, int max_gap_bars) {
    std::vector<GapInfo> result;

    sqlite3* db;
    sqlite3_open(db_path_.c_str(), &db);

    std::string sql = "SELECT timestamp FROM " + table + " ORDER BY timestamp ASC";
    sqlite3_stmt* stmt;
    sqlite3_prepare_v2(db, sql.c_str(), -1, &stmt, nullptr);

    Timestamp prev_ts;
    bool first = true;

    while (sqlite3_step(stmt) == SQLITE_ROW) {
        std::string ts_str = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 0));
        Timestamp ts = parse_iso(ts_str);

        if (!first) {
            auto diff = std::chrono::duration_cast<std::chrono::minutes>(ts - prev_ts);
            int gap_minutes = diff.count();

            // Assume 1-minute bars; gap > max_gap_bars minutes is anomalous
            if (gap_minutes > max_gap_bars) {
                GapInfo gap;
                gap.start = prev_ts;
                gap.end = ts;
                gap.missing_bars = gap_minutes - 1;
                result.push_back(gap);
            }
        }

        prev_ts = ts;
        first = false;
    }

    sqlite3_finalize(stmt);
    sqlite3_close(db);

    return result;
}

int PipelineMonitor::fill_small_gaps(const std::string& table, int max_gap_bars) {
    sqlite3* db;
    sqlite3_open(db_path_.c_str(), &db);

    auto gaps = detect_gaps(table, max_gap_bars);
    int filled = 0;

    for (const auto& gap : gaps) {
        if (gap.missing_bars > max_gap_bars) continue;  // Only fill small gaps

        // Query bars before and after gap
        std::string sql_before = "SELECT close FROM " + table + " WHERE timestamp < ? ORDER BY timestamp DESC LIMIT 1";
        std::string sql_after = "SELECT close FROM " + table + " WHERE timestamp > ? ORDER BY timestamp ASC LIMIT 1";

        sqlite3_stmt* stmt_before;
        sqlite3_stmt* stmt_after;
        sqlite3_prepare_v2(db, sql_before.c_str(), -1, &stmt_before, nullptr);
        sqlite3_prepare_v2(db, sql_after.c_str(), -1, &stmt_after, nullptr);

        // TODO: Bind timestamps, fetch close prices, linear interpolate, insert
        // For now: stub (full implementation requires timestamp binding helpers)

        sqlite3_finalize(stmt_before);
        sqlite3_finalize(stmt_after);
    }

    sqlite3_close(db);
    return filled;
}

DriftResult PipelineMonitor::detect_drift(const std::string& feature_name, int window) {
    DriftResult result;
    result.feature_name = feature_name;

    sqlite3* db;
    sqlite3_open(db_path_.c_str(), &db);

    // Fetch recent window and baseline window
    std::string sql = "SELECT feature_value FROM features WHERE feature_name = ? ORDER BY timestamp DESC LIMIT ?";
    sqlite3_stmt* stmt;
    sqlite3_prepare_v2(db, sql.c_str(), -1, &stmt, nullptr);
    sqlite3_bind_text(stmt, 1, feature_name.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_int(stmt, 2, window * 2);

    std::vector<double> values;
    while (sqlite3_step(stmt) == SQLITE_ROW) {
        values.push_back(sqlite3_column_double(stmt, 0));
    }
    sqlite3_finalize(stmt);
    sqlite3_close(db);

    if (values.size() < static_cast<size_t>(window * 2)) {
        result.is_drifting = false;
        result.kl_divergence = 0.0;
        return result;
    }

    // Split into recent and baseline
    std::vector<double> recent(values.begin(), values.begin() + window);
    std::vector<double> baseline(values.begin() + window, values.end());

    // Compute histograms (10 bins)
    auto make_hist = [](const std::vector<double>& data, int nbins = 10) {
        double min_val = *std::min_element(data.begin(), data.end());
        double max_val = *std::max_element(data.begin(), data.end());
        double bin_width = (max_val - min_val) / nbins;

        std::vector<double> hist(nbins, 0.0);
        for (double val : data) {
            int bin = std::min(nbins - 1, static_cast<int>((val - min_val) / bin_width));
            hist[bin] += 1.0;
        }

        // Normalize
        for (auto& h : hist) h /= data.size();
        return hist;
    };

    auto hist_recent = make_hist(recent);
    auto hist_baseline = make_hist(baseline);

    // KL divergence: sum(P * log(P / Q))
    double kl = 0.0;
    for (size_t i = 0; i < hist_recent.size(); ++i) {
        if (hist_recent[i] > 1e-9 && hist_baseline[i] > 1e-9) {
            kl += hist_recent[i] * std::log(hist_recent[i] / hist_baseline[i]);
        }
    }

    result.kl_divergence = kl;
    result.is_drifting = (kl > 0.1);  // Threshold

    return result;
}

std::pair<bool, double> PipelineMonitor::monitor_gold_dxy_correlation(int window) {
    sqlite3* db;
    sqlite3_open(db_path_.c_str(), &db);

    // Fetch gold closes
    const char* sql_gold = "SELECT close FROM gold_master ORDER BY timestamp DESC LIMIT ?";
    sqlite3_stmt* stmt_gold;
    sqlite3_prepare_v2(db, sql_gold, -1, &stmt_gold, nullptr);
    sqlite3_bind_int(stmt_gold, 1, window);

    std::vector<double> gold_prices;
    while (sqlite3_step(stmt_gold) == SQLITE_ROW) {
        gold_prices.push_back(sqlite3_column_double(stmt_gold, 0));
    }
    sqlite3_finalize(stmt_gold);

    // Fetch DXY values
    const char* sql_dxy = "SELECT value FROM macro_data WHERE series_id = 'DTWEXBGS' ORDER BY timestamp DESC LIMIT ?";
    sqlite3_stmt* stmt_dxy;
    sqlite3_prepare_v2(db, sql_dxy, -1, &stmt_dxy, nullptr);
    sqlite3_bind_int(stmt_dxy, 1, window);

    std::vector<double> dxy_values;
    while (sqlite3_step(stmt_dxy) == SQLITE_ROW) {
        dxy_values.push_back(sqlite3_column_double(stmt_dxy, 0));
    }
    sqlite3_finalize(stmt_dxy);
    sqlite3_close(db);

    if (gold_prices.size() < static_cast<size_t>(window) || dxy_values.size() < static_cast<size_t>(window)) {
        return {false, 0.0};
    }

    // Compute correlation
    double sum_x = 0.0, sum_y = 0.0, sum_xy = 0.0, sum_xx = 0.0, sum_yy = 0.0;
    int n = std::min(gold_prices.size(), dxy_values.size());

    for (int i = 0; i < n; ++i) {
        double x = gold_prices[i];
        double y = dxy_values[i];
        sum_x += x;
        sum_y += y;
        sum_xy += x * y;
        sum_xx += x * x;
        sum_yy += y * y;
    }

    double mean_x = sum_x / n;
    double mean_y = sum_y / n;
    double cov = (sum_xy / n) - mean_x * mean_y;
    double std_x = std::sqrt((sum_xx / n) - mean_x * mean_x);
    double std_y = std::sqrt((sum_yy / n) - mean_y * mean_y);

    double corr = 0.0;
    if (std_x > 1e-9 && std_y > 1e-9) {
        corr = cov / (std_x * std_y);
    }

    // Gold-DXY typically negative; flag if positive for extended period
    bool inverted = (corr > 0.0);

    return {inverted, corr};
}

HealthSummary PipelineMonitor::get_health_summary(
    const std::unordered_map<std::string, int>& thresholds
) {
    HealthSummary summary;
    summary.staleness = check_staleness(thresholds);
    summary.gaps = detect_gaps("gold_master", 5);

    auto [inverted, corr] = monitor_gold_dxy_correlation(20);
    summary.gold_dxy_correlation = corr;
    summary.gold_dxy_inverted = inverted;

    // Overall healthy if no stale sources, no gaps, correlation normal
    summary.overall_healthy = true;
    for (const auto& [source, status] : summary.staleness) {
        if (status.is_stale) summary.overall_healthy = false;
    }
    if (!summary.gaps.empty()) summary.overall_healthy = false;
    if (summary.gold_dxy_inverted) summary.overall_healthy = false;

    return summary;
}

} // namespace dominion
