#include "dominion/storage.hpp"
#include "dominion/sqlite3_wrapper.h"
#include <nlohmann/json.hpp>
#include <stdexcept>
#include <sstream>
#include <iomanip>

using json = nlohmann::json;

namespace dominion {

namespace {
    std::string to_iso8601(const Timestamp& ts) {
        auto t = std::chrono::system_clock::to_time_t(ts);
        std::ostringstream oss;
        oss << std::put_time(std::gmtime(&t), "%Y-%m-%dT%H:%M:%SZ");
        return oss.str();
    }

    Timestamp from_iso8601(const std::string& s) {
        std::tm tm = {};
        std::istringstream ss(s);
        ss >> std::get_time(&tm, "%Y-%m-%dT%H:%M:%SZ");
        return std::chrono::system_clock::from_time_t(std::mktime(&tm));
    }

    void bind_timestamp(sqlite3_stmt* stmt, int idx, const Timestamp& ts) {
        sqlite3_bind_text(stmt, idx, to_iso8601(ts).c_str(), -1, SQLITE_TRANSIENT);
    }

    Timestamp get_timestamp(sqlite3_stmt* stmt, int idx) {
        const char* text = reinterpret_cast<const char*>(sqlite3_column_text(stmt, idx));
        if (!text) return Timestamp();
        return from_iso8601(text);
    }
}

// PipelineRun methods
void Storage::log_run_start(PipelineRun& run) {
    const char* sql = "INSERT INTO pipeline_runs (run_id, started_at, status, sources_fetched, features_computed) "
                      "VALUES (?, ?, ?, 0, 0)";
    sqlite3_stmt* stmt;
    sqlite3_prepare_v2(impl_->db(), sql, -1, &stmt, nullptr);
    
    sqlite3_bind_text(stmt, 1, run.run_id.c_str(), -1, SQLITE_TRANSIENT);
    bind_timestamp(stmt, 2, run.started_at);
    sqlite3_bind_text(stmt, 3, run.status.c_str(), -1, SQLITE_TRANSIENT);
    
    if (sqlite3_step(stmt) != SQLITE_DONE) {
        sqlite3_finalize(stmt);
        throw std::runtime_error("Failed to log run start");
    }
    sqlite3_finalize(stmt);
}

void Storage::log_run_complete(const PipelineRun& run) {
    json errors_json = run.errors;
    
    const char* sql = "UPDATE pipeline_runs SET completed_at = ?, status = ?, "
                      "sources_fetched = ?, features_computed = ?, errors_json = ? "
                      "WHERE run_id = ?";
    sqlite3_stmt* stmt;
    sqlite3_prepare_v2(impl_->db(), sql, -1, &stmt, nullptr);
    
    if (run.completed_at.has_value()) {
        bind_timestamp(stmt, 1, *run.completed_at);
    } else {
        sqlite3_bind_null(stmt, 1);
    }
    sqlite3_bind_text(stmt, 2, run.status.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_int(stmt, 3, run.sources_fetched);
    sqlite3_bind_int(stmt, 4, run.features_computed);
    sqlite3_bind_text(stmt, 5, errors_json.dump().c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 6, run.run_id.c_str(), -1, SQLITE_TRANSIENT);
    
    sqlite3_step(stmt);
    sqlite3_finalize(stmt);
}

PipelineRun Storage::get_last_run() {
    const char* sql = "SELECT run_id, started_at, completed_at, status, sources_fetched, features_computed "
                      "FROM pipeline_runs ORDER BY started_at DESC LIMIT 1";
    sqlite3_stmt* stmt;
    sqlite3_prepare_v2(impl_->db(), sql, -1, &stmt, nullptr);
    
    PipelineRun run;
    if (sqlite3_step(stmt) == SQLITE_ROW) {
        run.run_id = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 0));
        run.started_at = get_timestamp(stmt, 1);
        if (sqlite3_column_type(stmt, 2) != SQLITE_NULL) {
            run.completed_at = get_timestamp(stmt, 2);
        }
        run.status = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 3));
        run.sources_fetched = sqlite3_column_int(stmt, 4);
        run.features_computed = sqlite3_column_int(stmt, 5);
    }
    sqlite3_finalize(stmt);
    return run;
}

// Bar storage
void Storage::store_bars(const std::vector<Bar>& bars) {
    const char* sql = "INSERT OR REPLACE INTO gold_raw (source, timestamp, open, high, low, close, volume, quality_score) "
                      "VALUES (?, ?, ?, ?, ?, ?, ?, ?)";
    sqlite3_stmt* stmt;
    sqlite3_prepare_v2(impl_->db(), sql, -1, &stmt, nullptr);
    
    sqlite3_exec(impl_->db(), "BEGIN TRANSACTION", nullptr, nullptr, nullptr);
    for (const auto& bar : bars) {
        sqlite3_bind_text(stmt, 1, bar.source.c_str(), -1, SQLITE_TRANSIENT);
        bind_timestamp(stmt, 2, bar.timestamp);
        sqlite3_bind_double(stmt, 3, bar.open);
        sqlite3_bind_double(stmt, 4, bar.high);
        sqlite3_bind_double(stmt, 5, bar.low);
        sqlite3_bind_double(stmt, 6, bar.close);
        sqlite3_bind_int64(stmt, 7, bar.volume);
        sqlite3_bind_double(stmt, 8, bar.quality_score);
        sqlite3_step(stmt);
        sqlite3_reset(stmt);
    }
    sqlite3_exec(impl_->db(), "COMMIT", nullptr, nullptr, nullptr);
    sqlite3_finalize(stmt);
}

void Storage::store_macro(const std::vector<MacroData>& data) {
    const char* sql = "INSERT OR REPLACE INTO macro_data (series_id, timestamp, value, series_name) "
                      "VALUES (?, ?, ?, ?)";
    sqlite3_stmt* stmt;
    sqlite3_prepare_v2(impl_->db(), sql, -1, &stmt, nullptr);
    
    sqlite3_exec(impl_->db(), "BEGIN TRANSACTION", nullptr, nullptr, nullptr);
    for (const auto& md : data) {
        sqlite3_bind_text(stmt, 1, md.series_id.c_str(), -1, SQLITE_TRANSIENT);
        bind_timestamp(stmt, 2, md.timestamp);
        sqlite3_bind_double(stmt, 3, md.value);
        sqlite3_bind_text(stmt, 4, md.series_name.c_str(), -1, SQLITE_TRANSIENT);
        sqlite3_step(stmt);
        sqlite3_reset(stmt);
    }
    sqlite3_exec(impl_->db(), "COMMIT", nullptr, nullptr, nullptr);
    sqlite3_finalize(stmt);
}

void Storage::store_cot(const std::vector<COTData>& data) {
    const char* sql = "INSERT OR REPLACE INTO cot_data (report_date, commercial_long, commercial_short, "
                      "noncommercial_long, noncommercial_short, open_interest, net_commercial, speculator_sentiment) "
                      "VALUES (?, ?, ?, ?, ?, ?, ?, ?)";
    sqlite3_stmt* stmt;
    sqlite3_prepare_v2(impl_->db(), sql, -1, &stmt, nullptr);
    
    sqlite3_exec(impl_->db(), "BEGIN TRANSACTION", nullptr, nullptr, nullptr);
    for (const auto& cot : data) {
        bind_timestamp(stmt, 1, cot.report_date);
        sqlite3_bind_int64(stmt, 2, cot.commercial_long);
        sqlite3_bind_int64(stmt, 3, cot.commercial_short);
        sqlite3_bind_int64(stmt, 4, cot.noncommercial_long);
        sqlite3_bind_int64(stmt, 5, cot.noncommercial_short);
        sqlite3_bind_int64(stmt, 6, cot.open_interest);
        sqlite3_bind_int64(stmt, 7, cot.net_commercial);
        sqlite3_bind_double(stmt, 8, cot.speculator_sentiment);
        sqlite3_step(stmt);
        sqlite3_reset(stmt);
    }
    sqlite3_exec(impl_->db(), "COMMIT", nullptr, nullptr, nullptr);
    sqlite3_finalize(stmt);
}

void Storage::store_fused_bars(const std::vector<FusedBar>& bars) {
    const char* sql = "INSERT OR REPLACE INTO gold_master (timestamp, open, high, low, close, volume, "
                      "fused_price, fused_confidence, source_weights_json, anomaly_flag, regime) "
                      "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";
    sqlite3_stmt* stmt;
    sqlite3_prepare_v2(impl_->db(), sql, -1, &stmt, nullptr);
    
    sqlite3_exec(impl_->db(), "BEGIN TRANSACTION", nullptr, nullptr, nullptr);
    for (const auto& bar : bars) {
        json weights = bar.source_weights;
        
        bind_timestamp(stmt, 1, bar.timestamp);
        sqlite3_bind_double(stmt, 2, bar.open);
        sqlite3_bind_double(stmt, 3, bar.high);
        sqlite3_bind_double(stmt, 4, bar.low);
        sqlite3_bind_double(stmt, 5, bar.close);
        sqlite3_bind_int64(stmt, 6, bar.volume);
        sqlite3_bind_double(stmt, 7, bar.fused_price);
        sqlite3_bind_double(stmt, 8, bar.fused_confidence);
        sqlite3_bind_text(stmt, 9, weights.dump().c_str(), -1, SQLITE_TRANSIENT);
        sqlite3_bind_int(stmt, 10, bar.anomaly_flag ? 1 : 0);
        sqlite3_bind_text(stmt, 11, bar.regime.c_str(), -1, SQLITE_TRANSIENT);
        sqlite3_step(stmt);
        sqlite3_reset(stmt);
    }
    sqlite3_exec(impl_->db(), "COMMIT", nullptr, nullptr, nullptr);
    sqlite3_finalize(stmt);
}

std::vector<FusedBar> Storage::load_fused_bars(int limit) {
    std::vector<FusedBar> result;
    const char* sql = "SELECT timestamp, open, high, low, close, volume, fused_price, fused_confidence, "
                      "source_weights_json, anomaly_flag, regime FROM gold_master ORDER BY timestamp DESC LIMIT ?";
    sqlite3_stmt* stmt;
    sqlite3_prepare_v2(impl_->db(), sql, -1, &stmt, nullptr);
    sqlite3_bind_int(stmt, 1, limit);
    
    while (sqlite3_step(stmt) == SQLITE_ROW) {
        FusedBar bar;
        bar.timestamp = get_timestamp(stmt, 0);
        bar.open = sqlite3_column_double(stmt, 1);
        bar.high = sqlite3_column_double(stmt, 2);
        bar.low = sqlite3_column_double(stmt, 3);
        bar.close = sqlite3_column_double(stmt, 4);
        bar.volume = sqlite3_column_int64(stmt, 5);
        bar.fused_price = sqlite3_column_double(stmt, 6);
        bar.fused_confidence = sqlite3_column_double(stmt, 7);
        
        const char* weights_json = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 8));
        if (weights_json) {
            auto j = json::parse(weights_json);
            bar.source_weights = j.get<std::unordered_map<std::string, double>>();
        }
        
        bar.anomaly_flag = sqlite3_column_int(stmt, 9) != 0;
        const char* regime = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 10));
        if (regime) bar.regime = regime;
        
        result.push_back(bar);
    }
    sqlite3_finalize(stmt);
    return result;
}

// Features
void Storage::store_features(const std::vector<Feature>& features) {
    const char* sql = "INSERT OR REPLACE INTO features (timestamp, feature_name, feature_value, feature_version, ic_252) "
                      "VALUES (?, ?, ?, ?, ?)";
    sqlite3_stmt* stmt;
    sqlite3_prepare_v2(impl_->db(), sql, -1, &stmt, nullptr);
    
    sqlite3_exec(impl_->db(), "BEGIN TRANSACTION", nullptr, nullptr, nullptr);
    for (const auto& f : features) {
        bind_timestamp(stmt, 1, f.timestamp);
        sqlite3_bind_text(stmt, 2, f.name.c_str(), -1, SQLITE_TRANSIENT);
        sqlite3_bind_double(stmt, 3, f.value);
        sqlite3_bind_text(stmt, 4, f.version.c_str(), -1, SQLITE_TRANSIENT);
        if (f.ic_252.has_value()) {
            sqlite3_bind_double(stmt, 5, *f.ic_252);
        } else {
            sqlite3_bind_null(stmt, 5);
        }
        sqlite3_step(stmt);
        sqlite3_reset(stmt);
    }
    sqlite3_exec(impl_->db(), "COMMIT", nullptr, nullptr, nullptr);
    sqlite3_finalize(stmt);
}

std::unordered_map<std::string, double> Storage::get_feature_importance(int top_n) {
    std::unordered_map<std::string, double> result;
    const char* sql = "SELECT feature_name, AVG(ABS(ic_252)) as avg_ic FROM features "
                      "WHERE ic_252 IS NOT NULL GROUP BY feature_name ORDER BY avg_ic DESC LIMIT ?";
    sqlite3_stmt* stmt;
    sqlite3_prepare_v2(impl_->db(), sql, -1, &stmt, nullptr);
    sqlite3_bind_int(stmt, 1, top_n);
    
    while (sqlite3_step(stmt) == SQLITE_ROW) {
        std::string name = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 0));
        double ic = sqlite3_column_double(stmt, 1);
        result[name] = ic;
    }
    sqlite3_finalize(stmt);
    return result;
}

// Source health
void Storage::store_source_health(const std::vector<SourceHealth>& health) {
    const char* sql = "INSERT OR REPLACE INTO source_health (source, last_fetch, status, latency_ms, error_count, trust_score) "
                      "VALUES (?, ?, ?, ?, ?, ?)";
    sqlite3_stmt* stmt;
    sqlite3_prepare_v2(impl_->db(), sql, -1, &stmt, nullptr);
    
    for (const auto& h : health) {
        sqlite3_bind_text(stmt, 1, h.source.c_str(), -1, SQLITE_TRANSIENT);
        bind_timestamp(stmt, 2, h.last_fetch);
        sqlite3_bind_text(stmt, 3, h.status.c_str(), -1, SQLITE_TRANSIENT);
        sqlite3_bind_double(stmt, 4, h.latency_ms);
        sqlite3_bind_int(stmt, 5, h.error_count);
        sqlite3_bind_double(stmt, 6, h.trust_score);
        sqlite3_step(stmt);
        sqlite3_reset(stmt);
    }
    sqlite3_finalize(stmt);
}

// Anomalies
void Storage::log_anomaly(const Anomaly& anomaly) {
    const char* sql = "INSERT OR REPLACE INTO anomaly_log (timestamp, anomaly_type, description, severity, source, value) "
                      "VALUES (?, ?, ?, ?, ?, ?)";
    sqlite3_stmt* stmt;
    sqlite3_prepare_v2(impl_->db(), sql, -1, &stmt, nullptr);
    
    bind_timestamp(stmt, 1, anomaly.timestamp);
    sqlite3_bind_text(stmt, 2, anomaly.type.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 3, anomaly.description.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 4, anomaly.severity.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 5, anomaly.source.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_double(stmt, 6, anomaly.value);
    sqlite3_step(stmt);
    sqlite3_finalize(stmt);
}

std::vector<Anomaly> Storage::get_recent_anomalies(int hours) {
    std::vector<Anomaly> result;
    const char* sql = "SELECT timestamp, anomaly_type, description, severity, source, value FROM anomaly_log "
                      "WHERE timestamp > datetime('now', '-' || ? || ' hours') ORDER BY timestamp DESC";
    sqlite3_stmt* stmt;
    sqlite3_prepare_v2(impl_->db(), sql, -1, &stmt, nullptr);
    sqlite3_bind_int(stmt, 1, hours);
    
    while (sqlite3_step(stmt) == SQLITE_ROW) {
        Anomaly a;
        a.timestamp = get_timestamp(stmt, 0);
        a.type = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 1));
        a.description = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 2));
        a.severity = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 3));
        a.source = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 4));
        a.value = sqlite3_column_double(stmt, 5);
        result.push_back(a);
    }
    sqlite3_finalize(stmt);
    return result;
}

// Reports
void Storage::store_report(const std::string& report_date, const std::string& report_text, bool ragd_stored) {
    const char* sql = "INSERT OR REPLACE INTO intelligence_reports (report_date, report_text, ragd_stored) VALUES (?, ?, ?)";
    sqlite3_stmt* stmt;
    sqlite3_prepare_v2(impl_->db(), sql, -1, &stmt, nullptr);
    sqlite3_bind_text(stmt, 1, report_date.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 2, report_text.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_int(stmt, 3, ragd_stored ? 1 : 0);
    sqlite3_step(stmt);
    sqlite3_finalize(stmt);
}

// Stubs for remaining methods
void Storage::store_ticks(const std::vector<Tick>&) {}
std::vector<Tick> Storage::load_ticks(int) { return {}; }
std::vector<Feature> Storage::load_features(const std::string&, int) { return {}; }
void Storage::store_regimes(const std::vector<RegimeLabel>&) {}
std::vector<RegimeLabel> Storage::load_regimes(int) { return {}; }
std::vector<SourceHealth> Storage::load_source_health() { return {}; }
std::string Storage::get_latest_report() { return ""; }

} // namespace dominion
