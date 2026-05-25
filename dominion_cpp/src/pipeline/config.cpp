#include "dominion/config.hpp"
#include <cstdlib>
#include <stdexcept>

namespace dominion {

Config Config::from_env() {
    Config cfg;

    // Repo root
    const char* home = std::getenv("HOME");
    if (!home) throw std::runtime_error("HOME not set");
    cfg.repo_root = std::filesystem::path(home) / "Dominion";

    // Paths
    cfg.duckdb_path = cfg.repo_root / "data" / "dominion.duckdb";
    cfg.reports_dir = cfg.repo_root / "reports";
    cfg.raw_data_root = cfg.repo_root / "data" / "raw" / "mt5";
    cfg.normalized_root = cfg.repo_root / "data" / "normalized" / "mt5";

    // API keys
    const char* av_key = std::getenv("ALPHAVANTAGE_API_KEY");
    const char* fred_key = std::getenv("FRED_API_KEY");
    if (av_key) cfg.alphavantage_api_key = av_key;
    if (fred_key) cfg.fred_api_key = fred_key;

    // FRED series
    cfg.fred_series = {
        {"DGS10", "10-Year Treasury Constant Maturity Rate"},
        {"DGS2", "2-Year Treasury Constant Maturity Rate"},
        {"DFII10", "10-Year Treasury Inflation-Indexed Security"},
        {"DEXUSEU", "U.S. / Euro Foreign Exchange Rate"},
        {"DTWEXBGS", "Trade Weighted U.S. Dollar Index: Broad, Goods and Services"},
        {"VIXCLS", "CBOE Volatility Index: VIX"},
        {"CPIAUCSL", "Consumer Price Index for All Urban Consumers"},
        {"FEDFUNDS", "Federal Funds Effective Rate"},
        {"T10Y2Y", "10-Year Treasury Constant Maturity Minus 2-Year"},
        {"T5YIFR", "5-Year, 5-Year Forward Inflation Expectation Rate"},
    };

    // COT URLs (2022-2026)
    cfg.cot_urls = {
        "https://www.cftc.gov/files/dea/history/fut_disagg_txt_2022.zip",
        "https://www.cftc.gov/files/dea/history/fut_disagg_txt_2023.zip",
        "https://www.cftc.gov/files/dea/history/fut_disagg_txt_2024.zip",
        "https://www.cftc.gov/files/dea/history/fut_disagg_txt_2025.zip",
        "https://www.cftc.gov/files/dea/history/fut_disagg_txt_2026.zip",
    };

    // FOMC dates 2026 (8 meetings)
    cfg.fomc_dates_2026 = {
        "2026-01-28", "2026-03-18", "2026-05-06", "2026-06-17",
        "2026-07-29", "2026-09-16", "2026-11-04", "2026-12-16",
    };

    return cfg;
}

Config Config::load(const std::filesystem::path& config_path) {
    // For now just use env vars
    // TODO: parse YAML/JSON config file if provided
    return from_env();
}

} // namespace dominion
