#pragma once

#include <filesystem>
#include <string>
#include <unordered_map>
#include <vector>

namespace dominion {

struct KalmanConfig {
    double process_noise;
    double observation_noise;
};

struct Config {
    // Paths
    std::filesystem::path repo_root;
    std::filesystem::path duckdb_path;
    std::filesystem::path reports_dir;
    std::filesystem::path raw_data_root;
    std::filesystem::path normalized_root;

    // API keys
    std::string alphavantage_api_key;
    std::string fred_api_key;

    // RAGD
    std::string ragd_url = "http://127.0.0.1:7474";
    std::string bus_url = "ws://127.0.0.1:7474/bus";

    // Sources
    std::vector<std::string> yahoo_tickers = {"GC=F", "GLD"};
    std::string yahoo_period = "5y";
    std::unordered_map<std::string, std::string> fred_series;
    std::vector<std::string> cot_urls;
    std::string cot_gold_code = "088691";

    // MT5
    std::string mt5_symbol = "XAUUSD";
    std::string mt5_timeframe = "M1";
    int mt5_tick_interval_ms = 250;
    int mt5_bar_interval_sec = 10;
    int mt5_heartbeat_sec = 10;

    // Kalman filter bank
    std::unordered_map<std::string, KalmanConfig> kalman_filters = {
        {"tick", {0.001, 0.1}},
        {"m1",   {0.0005, 0.05}},
        {"m15",  {0.0001, 0.01}},
        {"h1",   {0.00005, 0.005}},
        {"h4",   {0.00001, 0.001}},
        {"d1",   {0.000005, 0.0005}},
    };

    // Feature windows
    std::vector<int> feature_windows = {5, 10, 20, 50, 100, 252};
    int ic_window = 252;

    // Health
    std::unordered_map<std::string, int> staleness_hours = {
        {"yahoo", 24}, {"fred", 72}, {"alphavantage", 24},
        {"cot", 168}, {"mt5", 1},
    };
    double anomaly_z_flag = 3.0;
    double anomaly_z_quarantine = 5.0;

    // Calendar
    std::vector<std::string> fomc_dates_2026;

    static Config load(const std::filesystem::path& config_path = "");
    static Config from_env();
};

} // namespace dominion
