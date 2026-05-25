#include "dominion/sources.hpp"
#include <httplib.h>
#include <nlohmann/json.hpp>
#include <sstream>
#include <thread>
#include <chrono>
#include <ctime>

using json = nlohmann::json;

namespace dominion {

namespace {
    Timestamp parse_unix(int64_t ts) {
        return Timestamp(std::chrono::seconds(ts));
    }

    std::string format_timestamp(const Timestamp& ts) {
        auto t = std::chrono::system_clock::to_time_t(ts);
        std::ostringstream oss;
        oss << std::put_time(std::gmtime(&t), "%Y-%m-%dT%H:%M:%SZ");
        return oss.str();
    }
}

YahooSource::YahooSource(const Config& config) : config_(config) {}

SourceResult YahooSource::fetch() {
    SourceResult result;
    result.source_name = "yahoo";

    auto start = std::chrono::steady_clock::now();

    // Yahoo Finance API v8: https://query1.finance.yahoo.com/v8/finance/chart/{symbol}
    httplib::Client cli("https://query1.finance.yahoo.com");
    cli.set_read_timeout(30);
    cli.set_connection_timeout(10);

    std::vector<std::string> symbols = config_.yahoo_tickers;
    if (symbols.empty()) symbols = {"GC=F", "GLD"};

    for (const auto& symbol : symbols) {
        // Build query params
        std::ostringstream path;
        path << "/v8/finance/chart/" << symbol
             << "?interval=1d&range=" << config_.yahoo_period;

        // Retry logic: 3 attempts with exponential backoff
        bool success = false;
        std::string error_msg;

        for (int attempt = 0; attempt < 3; ++attempt) {
            if (attempt > 0) {
                std::this_thread::sleep_for(std::chrono::milliseconds(1000 * (1 << attempt)));
            }

            auto res = cli.Get(path.str().c_str());
            if (!res) {
                error_msg = "HTTP request failed";
                continue;
            }

            if (res->status != 200) {
                error_msg = "HTTP " + std::to_string(res->status);
                continue;
            }

            try {
                auto j = json::parse(res->body);

                // Navigate Yahoo's nested structure
                if (!j.contains("chart") || !j["chart"].contains("result") ||
                    j["chart"]["result"].empty()) {
                    error_msg = "Empty response";
                    continue;
                }

                auto result_obj = j["chart"]["result"][0];
                if (!result_obj.contains("timestamp") || !result_obj.contains("indicators")) {
                    error_msg = "Missing timestamp or indicators";
                    continue;
                }

                auto timestamps = result_obj["timestamp"];
                auto quote = result_obj["indicators"]["quote"][0];

                auto open_arr = quote["open"];
                auto high_arr = quote["high"];
                auto low_arr = quote["low"];
                auto close_arr = quote["close"];
                auto volume_arr = quote["volume"];

                // Parse bars
                for (size_t i = 0; i < timestamps.size(); ++i) {
                    // Skip if any value is null
                    if (close_arr[i].is_null() || open_arr[i].is_null() ||
                        high_arr[i].is_null() || low_arr[i].is_null()) {
                        continue;
                    }

                    Bar bar;
                    bar.timestamp = parse_unix(timestamps[i].get<int64_t>());
                    bar.open = open_arr[i].get<double>();
                    bar.high = high_arr[i].get<double>();
                    bar.low = low_arr[i].get<double>();
                    bar.close = close_arr[i].get<double>();
                    bar.volume = volume_arr[i].is_null() ? 0 : volume_arr[i].get<int64_t>();
                    bar.source = "yahoo";
                    bar.quality_score = 1.0;

                    // Validation: price in [50, 6000] range, no NaN, volume >= 0
                    if (std::isnan(bar.close) || bar.close < 50.0 || bar.close > 6000.0) {
                        continue;
                    }
                    if (bar.volume < 0) bar.volume = 0;

                    result.bars.push_back(bar);
                }

                success = true;
                break;

            } catch (const std::exception& e) {
                error_msg = std::string("Parse error: ") + e.what();
                continue;
            }
        }

        if (!success) {
            result.error = "Yahoo " + symbol + ": " + error_msg;
            result.success = false;
            return result;
        }
    }

    auto end = std::chrono::steady_clock::now();
    result.latency_ms = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();
    result.success = true;

    return result;
}

} // namespace dominion
