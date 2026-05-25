#include "dominion/sources.hpp"
#include <httplib.h>
#include <nlohmann/json.hpp>
#include <fstream>
#include <filesystem>
#include <thread>
#include <sstream>

using json = nlohmann::json;

namespace dominion {

namespace {
    Timestamp parse_date(const std::string& date_str) {
        std::tm tm = {};
        std::istringstream ss(date_str);
        ss >> std::get_time(&tm, "%Y-%m-%d");
        return std::chrono::system_clock::from_time_t(std::mktime(&tm));
    }

    bool cache_valid(const std::filesystem::path& cache_path, int max_age_hours = 23) {
        if (!std::filesystem::exists(cache_path)) return false;

        auto mtime = std::filesystem::last_write_time(cache_path);
        auto now = std::filesystem::file_time_type::clock::now();
        auto age = std::chrono::duration_cast<std::chrono::hours>(now - mtime);

        return age.count() < max_age_hours;
    }
}

AlphaVantageSource::AlphaVantageSource(const Config& config) : config_(config) {
    cache_path_ = "/tmp/av_gld_cache.json";
}

SourceResult AlphaVantageSource::fetch() {
    SourceResult result;
    result.source_name = "alphavantage";

    if (config_.alphavantage_api_key.empty()) {
        result.error = "AlphaVantage API key not set";
        result.success = false;
        return result;
    }

    auto start = std::chrono::steady_clock::now();

    // Check cache first (23-hour TTL to stay under 25 calls/day limit)
    if (cache_valid(cache_path_, 23)) {
        try {
            std::ifstream ifs(cache_path_);
            json cached = json::parse(ifs);

            for (const auto& item : cached) {
                Bar bar;
                bar.timestamp = parse_date(item["date"].get<std::string>());
                bar.open = item["open"].get<double>();
                bar.high = item["high"].get<double>();
                bar.low = item["low"].get<double>();
                bar.close = item["close"].get<double>();
                bar.volume = item["volume"].get<int64_t>();
                bar.source = "alphavantage";
                bar.quality_score = 0.9;  // slight discount vs Yahoo

                result.bars.push_back(bar);
            }

            result.success = true;
            auto end = std::chrono::steady_clock::now();
            result.latency_ms = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();
            return result;

        } catch (const std::exception&) {
            // Cache corrupted, fetch fresh
        }
    }

    // Fetch from API (with 13-second delay to respect rate limits)
    std::this_thread::sleep_for(std::chrono::seconds(13));

    httplib::Client cli("https://www.alphavantage.co");
    cli.set_read_timeout(30);
    cli.set_connection_timeout(10);

    std::ostringstream path;
    path << "/query?function=TIME_SERIES_DAILY"
         << "&symbol=GLD"
         << "&outputsize=full"
         << "&apikey=" << config_.alphavantage_api_key;

    auto res = cli.Get(path.str().c_str());

    if (!res || res->status != 200) {
        result.error = "API request failed";
        result.success = false;
        return result;
    }

    try {
        auto j = json::parse(res->body);

        // Check for rate limit message
        if (j.contains("Note") || j.contains("Information")) {
            result.error = "Rate limited";
            result.success = false;
            return result;
        }

        if (!j.contains("Time Series (Daily)")) {
            result.error = "Missing time series data";
            result.success = false;
            return result;
        }

        json cache_data = json::array();
        auto ts_obj = j["Time Series (Daily)"];

        for (auto it = ts_obj.begin(); it != ts_obj.end(); ++it) {
            std::string date = it.key();
            auto day_data = it.value();

            Bar bar;
            bar.timestamp = parse_date(date);
            bar.open = std::stod(day_data["1. open"].get<std::string>());
            bar.high = std::stod(day_data["2. high"].get<std::string>());
            bar.low = std::stod(day_data["3. low"].get<std::string>());
            bar.close = std::stod(day_data["4. close"].get<std::string>());
            bar.volume = std::stoll(day_data["5. volume"].get<std::string>());
            bar.source = "alphavantage";
            bar.quality_score = 0.9;

            // Validation: GLD ETF price in [50, 500] range
            if (std::isnan(bar.close) || bar.close < 50.0 || bar.close > 500.0) {
                continue;
            }

            result.bars.push_back(bar);

            // Cache format
            cache_data.push_back({
                {"date", date},
                {"open", bar.open},
                {"high", bar.high},
                {"low", bar.low},
                {"close", bar.close},
                {"volume", bar.volume}
            });
        }

        // Write cache
        std::ofstream ofs(cache_path_);
        ofs << cache_data.dump(2);

        result.success = true;

    } catch (const std::exception& e) {
        result.error = std::string("Parse error: ") + e.what();
        result.success = false;
    }

    auto end = std::chrono::steady_clock::now();
    result.latency_ms = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();

    return result;
}

} // namespace dominion
