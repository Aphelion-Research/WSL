"""DuckDB schema definitions for the pipeline."""
import duckdb
from pathlib import Path

SCHEMA_DDL = """
-- Raw gold price data from all sources
CREATE TABLE IF NOT EXISTS gold_raw (
    source VARCHAR NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE NOT NULL,
    volume DOUBLE,
    fetch_time TIMESTAMP NOT NULL,
    quality_score DOUBLE,
    PRIMARY KEY (source, timestamp)
);

-- Kalman-fused gold master timeseries
CREATE TABLE IF NOT EXISTS gold_master (
    timestamp TIMESTAMP PRIMARY KEY,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE NOT NULL,
    volume DOUBLE,
    fused_price DOUBLE NOT NULL,
    fused_confidence DOUBLE NOT NULL,
    source_weights_json VARCHAR,
    anomaly_flag BOOLEAN DEFAULT FALSE,
    regime VARCHAR
);

-- Synthetic tick reconstruction
CREATE TABLE IF NOT EXISTS gold_ticks (
    timestamp TIMESTAMP NOT NULL,
    bar_timestamp TIMESTAMP NOT NULL,
    tick_price DOUBLE NOT NULL,
    confidence DOUBLE,
    PRIMARY KEY (timestamp, bar_timestamp)
);

-- FRED macro data
CREATE TABLE IF NOT EXISTS macro_data (
    series_id VARCHAR NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    value DOUBLE NOT NULL,
    series_name VARCHAR,
    PRIMARY KEY (series_id, timestamp)
);

-- CFTC COT data
CREATE TABLE IF NOT EXISTS cot_data (
    report_date DATE PRIMARY KEY,
    commercial_long DOUBLE,
    commercial_short DOUBLE,
    noncommercial_long DOUBLE,
    noncommercial_short DOUBLE,
    open_interest DOUBLE,
    net_commercial DOUBLE,
    speculator_sentiment DOUBLE
);

-- Feature store
CREATE TABLE IF NOT EXISTS features (
    timestamp TIMESTAMP NOT NULL,
    feature_name VARCHAR NOT NULL,
    feature_value DOUBLE,
    feature_version INTEGER DEFAULT 1,
    ic_252 DOUBLE,
    ic_updated_at TIMESTAMP,
    PRIMARY KEY (timestamp, feature_name, feature_version)
);

-- Regime labels
CREATE TABLE IF NOT EXISTS regime_labels (
    timestamp TIMESTAMP PRIMARY KEY,
    macro_regime VARCHAR,
    structural_regime VARCHAR,
    tactical_regime VARCHAR,
    micro_regime VARCHAR,
    confidence DOUBLE
);

-- Source health tracking
CREATE TABLE IF NOT EXISTS source_health (
    source VARCHAR PRIMARY KEY,
    last_fetch TIMESTAMP,
    status VARCHAR,
    latency_ms DOUBLE,
    error_count INTEGER DEFAULT 0,
    trust_score DOUBLE DEFAULT 0.5
);

-- Pipeline run logs
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id VARCHAR PRIMARY KEY,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    status VARCHAR,
    sources_fetched INTEGER,
    features_computed INTEGER,
    errors_json VARCHAR
);

-- Intelligence reports
CREATE TABLE IF NOT EXISTS intelligence_reports (
    report_date DATE PRIMARY KEY,
    report_text VARCHAR,
    ragd_stored BOOLEAN DEFAULT FALSE
);

-- Anomaly log
CREATE TABLE IF NOT EXISTS anomaly_log (
    timestamp TIMESTAMP NOT NULL,
    anomaly_type VARCHAR NOT NULL,
    description VARCHAR,
    severity VARCHAR,
    source VARCHAR,
    value DOUBLE,
    PRIMARY KEY (timestamp, anomaly_type, source)
);

-- Create indices for common queries
CREATE INDEX IF NOT EXISTS idx_gold_raw_timestamp ON gold_raw(timestamp);
CREATE INDEX IF NOT EXISTS idx_gold_master_timestamp ON gold_master(timestamp);
CREATE INDEX IF NOT EXISTS idx_features_timestamp ON features(timestamp);
CREATE INDEX IF NOT EXISTS idx_features_name ON features(feature_name);
CREATE INDEX IF NOT EXISTS idx_macro_timestamp ON macro_data(timestamp);
"""


def init_schema(db_path: Path) -> None:
    """Initialize DuckDB schema."""
    conn = duckdb.connect(str(db_path))
    conn.execute(SCHEMA_DDL)
    conn.close()


if __name__ == "__main__":
    from data_pipeline.config import DUCKDB_PATH
    init_schema(DUCKDB_PATH)
    print(f"Schema initialized at {DUCKDB_PATH}")
