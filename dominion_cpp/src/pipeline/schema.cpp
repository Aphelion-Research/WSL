#include "dominion/storage.hpp"
#include <sqlite3.h>
#include <stdexcept>
#include <string>

namespace dominion {

constexpr const char* DDL_SCHEMA = R"(
-- Raw source data
CREATE TABLE IF NOT EXISTS gold_raw (
    source TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    fetch_time TIMESTAMP,
    quality_score REAL,
    PRIMARY KEY (source, timestamp)
);
CREATE INDEX IF NOT EXISTS idx_gold_raw_timestamp ON gold_raw(timestamp);

-- Kalman-fused master table
CREATE TABLE IF NOT EXISTS gold_master (
    timestamp TIMESTAMP PRIMARY KEY,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    fused_price REAL NOT NULL,
    fused_confidence REAL NOT NULL,
    source_weights_json TEXT,
    anomaly_flag INTEGER DEFAULT 0,
    regime TEXT
);
CREATE INDEX IF NOT EXISTS idx_gold_master_timestamp ON gold_master(timestamp);

-- Synthetic tick reconstruction
CREATE TABLE IF NOT EXISTS gold_ticks (
    timestamp TIMESTAMP NOT NULL,
    bar_timestamp TIMESTAMP NOT NULL,
    tick_price REAL NOT NULL,
    confidence REAL NOT NULL,
    PRIMARY KEY (timestamp, bar_timestamp)
);

-- Macro data (FRED series)
CREATE TABLE IF NOT EXISTS macro_data (
    series_id TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    value REAL NOT NULL,
    series_name TEXT,
    PRIMARY KEY (series_id, timestamp)
);
CREATE INDEX IF NOT EXISTS idx_macro_timestamp ON macro_data(timestamp);

-- COT data
CREATE TABLE IF NOT EXISTS cot_data (
    report_date TIMESTAMP PRIMARY KEY,
    commercial_long INTEGER,
    commercial_short INTEGER,
    noncommercial_long INTEGER,
    noncommercial_short INTEGER,
    open_interest INTEGER,
    net_commercial INTEGER,
    speculator_sentiment REAL
);

-- Features (400+ computed features)
CREATE TABLE IF NOT EXISTS features (
    timestamp TIMESTAMP NOT NULL,
    feature_name TEXT NOT NULL,
    feature_value REAL,
    feature_version TEXT DEFAULT '1.0',
    ic_252 REAL,
    ic_updated_at TIMESTAMP,
    PRIMARY KEY (timestamp, feature_name, feature_version)
);
CREATE INDEX IF NOT EXISTS idx_features_timestamp ON features(timestamp);
CREATE INDEX IF NOT EXISTS idx_features_name ON features(feature_name);

-- Regime labels
CREATE TABLE IF NOT EXISTS regime_labels (
    timestamp TIMESTAMP PRIMARY KEY,
    macro_regime TEXT,
    structural_regime TEXT,
    tactical_regime TEXT,
    micro_regime TEXT,
    confidence REAL
);

-- Source health tracking
CREATE TABLE IF NOT EXISTS source_health (
    source TEXT PRIMARY KEY,
    last_fetch TIMESTAMP,
    status TEXT,
    latency_ms REAL,
    error_count INTEGER DEFAULT 0,
    trust_score REAL DEFAULT 0.5
);

-- Pipeline runs audit
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id TEXT PRIMARY KEY,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    status TEXT NOT NULL,
    sources_fetched INTEGER DEFAULT 0,
    features_computed INTEGER DEFAULT 0,
    errors_json TEXT
);

-- Intelligence reports
CREATE TABLE IF NOT EXISTS intelligence_reports (
    report_date TEXT PRIMARY KEY,
    report_text TEXT NOT NULL,
    ragd_stored INTEGER DEFAULT 0
);

-- Anomaly log
CREATE TABLE IF NOT EXISTS anomaly_log (
    timestamp TIMESTAMP NOT NULL,
    anomaly_type TEXT NOT NULL,
    description TEXT,
    severity TEXT,
    source TEXT,
    value REAL,
    PRIMARY KEY (timestamp, anomaly_type, source)
);
)";

class Storage::Impl {
public:
    explicit Impl(const std::string& db_path) : db_path_(db_path), db_(nullptr) {
        int rc = sqlite3_open(db_path.c_str(), &db_);
        if (rc != SQLITE_OK) {
            std::string err = sqlite3_errmsg(db_);
            sqlite3_close(db_);
            throw std::runtime_error("Failed to open database: " + err);
        }
    }

    ~Impl() {
        if (db_) sqlite3_close(db_);
    }

    void init_schema() {
        char* err_msg = nullptr;
        int rc = sqlite3_exec(db_, DDL_SCHEMA, nullptr, nullptr, &err_msg);
        if (rc != SQLITE_OK) {
            std::string err = err_msg;
            sqlite3_free(err_msg);
            throw std::runtime_error("Failed to initialize schema: " + err);
        }
    }

    sqlite3* db() { return db_; }

private:
    std::string db_path_;
    sqlite3* db_;
};

Storage::Storage(const std::string& db_path)
    : impl_(std::make_unique<Impl>(db_path)) {}

Storage::~Storage() = default;

void Storage::init_schema() {
    impl_->init_schema();
}

// Stub implementations for now - will implement in storage.cpp
void Storage::log_run_start(PipelineRun& run) {
    // TODO: INSERT INTO pipeline_runs
}

void Storage::log_run_complete(const PipelineRun& run) {
    // TODO: UPDATE pipeline_runs SET completed_at, status, errors_json
}

PipelineRun Storage::get_last_run() {
    // TODO: SELECT * FROM pipeline_runs ORDER BY started_at DESC LIMIT 1
    return {};
}

void Storage::store_bars(const std::vector<Bar>& bars) {
    // TODO: INSERT INTO gold_raw
}

void Storage::store_macro(const std::vector<MacroData>& data) {
    // TODO: INSERT INTO macro_data
}

void Storage::store_cot(const std::vector<COTData>& data) {
    // TODO: INSERT INTO cot_data
}

void Storage::store_fused_bars(const std::vector<FusedBar>& bars) {
    // TODO: INSERT INTO gold_master
}

std::vector<FusedBar> Storage::load_fused_bars(int limit) {
    // TODO: SELECT * FROM gold_master ORDER BY timestamp DESC LIMIT ?
    return {};
}

void Storage::store_ticks(const std::vector<Tick>& ticks) {
    // TODO: INSERT INTO gold_ticks
}

std::vector<Tick> Storage::load_ticks(int limit) {
    // TODO: SELECT * FROM gold_ticks ORDER BY timestamp DESC LIMIT ?
    return {};
}

void Storage::store_features(const std::vector<Feature>& features) {
    // TODO: INSERT INTO features
}

std::vector<Feature> Storage::load_features(const std::string& name, int limit) {
    // TODO: SELECT * FROM features WHERE feature_name = ? OR ? = '' LIMIT ?
    return {};
}

std::unordered_map<std::string, double> Storage::get_feature_importance(int top_n) {
    // TODO: SELECT feature_name, AVG(ABS(ic_252)) GROUP BY feature_name ORDER BY DESC LIMIT ?
    return {};
}

void Storage::store_regimes(const std::vector<RegimeLabel>& regimes) {
    // TODO: INSERT INTO regime_labels
}

std::vector<RegimeLabel> Storage::load_regimes(int limit) {
    // TODO: SELECT * FROM regime_labels ORDER BY timestamp DESC LIMIT ?
    return {};
}

void Storage::store_source_health(const std::vector<SourceHealth>& health) {
    // TODO: INSERT OR REPLACE INTO source_health
}

std::vector<SourceHealth> Storage::load_source_health() {
    // TODO: SELECT * FROM source_health
    return {};
}

void Storage::log_anomaly(const Anomaly& anomaly) {
    // TODO: INSERT INTO anomaly_log
}

std::vector<Anomaly> Storage::get_recent_anomalies(int hours) {
    // TODO: SELECT * FROM anomaly_log WHERE timestamp > datetime('now', '-' || ? || ' hours')
    return {};
}

void Storage::store_report(const std::string& report_date, const std::string& report_text, bool ragd_stored) {
    // TODO: INSERT OR REPLACE INTO intelligence_reports
}

std::string Storage::get_latest_report() {
    // TODO: SELECT report_text FROM intelligence_reports ORDER BY report_date DESC LIMIT 1
    return "";
}

} // namespace dominion
