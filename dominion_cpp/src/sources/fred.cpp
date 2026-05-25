#include "dominion/sources.hpp"
#include <httplib.h>
#include <nlohmann/json.hpp>
#include <sstream>
#include <ctime>

using json = nlohmann::json;

namespace dominion {

namespace {
    Timestamp parse_date(const std::string& date_str) {
        std::tm tm = {};
        std::istringstream ss(date_str);
        ss >> std::get_time(&tm, "%Y-%m-%d");
        return std::chrono::system_clock::from_time_t(std::mktime(&tm));
    }

    std::string format_date(const Timestamp& ts) {
        auto t = std::chrono::system_clock::to_time_t(ts);
        std::ostringstream oss;
        oss << std::put_time(std::gmtime(&t), "%Y-%m-%d");
        return oss.str();
    }
}

FREDSource::FREDSource(const Config& config) : config_(config) {}

SourceResult FREDSource::fetch() {
    SourceResult result;
    result.source_name = "fred";

    if (config_.fred_api_key.empty()) {
        result.error = "FRED API key not set";
        result.success = false;
        return result;
    }

    auto start = std::chrono::steady_clock::now();

    httplib::Client cli("https://api.stlouisfed.org");
    cli.set_read_timeout(30);
    cli.set_connection_timeout(10);

    // Date range: last 5 years
    auto now = std::chrono::system_clock::now();
    auto five_years_ago = now - std::chrono::hours(24 * 365 * 5);
    std::string start_date = format_date(five_years_ago);
    std::string end_date = format_date(now);

    // Fetch all configured series
    for (const auto& [series_id, series_name] : config_.fred_series) {
        std::ostringstream path;
        path << "/fred/series/observations"
             << "?series_id=" << series_id
             << "&api_key=" << config_.fred_api_key
             << "&file_type=json"
             << "&observation_start=" << start_date
             << "&observation_end=" << end_date;

        auto res = cli.Get(path.str().c_str());
        if (!res || res->status != 200) {
            continue;  // Skip failed series, don't fail entire fetch
        }

        try {
            auto j = json::parse(res->body);

            if (!j.contains("observations")) continue;

            for (const auto& obs : j["observations"]) {
                std::string date = obs["date"].get<std::string>();
                std::string value_str = obs["value"].get<std::string>();

                // FRED uses "." for missing data
                if (value_str == ".") continue;

                double value = std::stod(value_str);

                MacroData md;
                md.series_id = series_id;
                md.series_name = series_name;
                md.timestamp = parse_date(date);
                md.value = value;

                result.macro.push_back(md);
            }

        } catch (const std::exception& e) {
            // Skip parse errors, continue with other series
            continue;
        }
    }

    auto end = std::chrono::steady_clock::now();
    result.latency_ms = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();
    result.success = !result.macro.empty();

    if (!result.success) {
        result.error = "No FRED series fetched successfully";
    }

    return result;
}

} // namespace dominion
