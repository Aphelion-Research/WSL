#include "dominion/sources.hpp"
#include <nlohmann/json.hpp>
#include <array>
#include <memory>
#include <sstream>
#include <cstdio>

using json = nlohmann::json;

namespace dominion {

namespace {
    std::string exec_command(const std::string& cmd, int timeout_sec = 30) {
        std::array<char, 128> buffer;
        std::string result;

        // popen with timeout is tricky; simplified version without timeout
        std::unique_ptr<FILE, decltype(&pclose)> pipe(popen(cmd.c_str(), "r"), pclose);
        if (!pipe) {
            throw std::runtime_error("popen() failed");
        }

        while (fgets(buffer.data(), buffer.size(), pipe.get()) != nullptr) {
            result += buffer.data();
        }

        return result;
    }

    Timestamp parse_unix(int64_t ts) {
        return Timestamp(std::chrono::seconds(ts));
    }
}

MT5Source::MT5Source(const Config& config) : config_(config) {}

SourceResult MT5Source::fetch() {
    SourceResult result;
    result.source_name = "mt5";

    auto start = std::chrono::steady_clock::now();

    // Call domdata CLI: domdata xaurates (shortcut for XAUUSD D1 rates)
    // Or: python3 /path/to/domdata.py rates XAUUSD D1 --count 1000
    std::string cmd = config_.repo_root / "domdata" / "domdata.py";
    cmd += " xaurates";

    try {
        std::string output = exec_command(cmd, 30);

        if (output.empty()) {
            result.error = "Empty output from domdata CLI";
            result.success = false;
            return result;
        }

        // Parse JSON array
        auto j = json::parse(output);

        if (!j.is_array()) {
            result.error = "Expected JSON array from domdata";
            result.success = false;
            return result;
        }

        for (const auto& item : j) {
            Bar bar;
            bar.timestamp = parse_unix(item["time"].get<int64_t>());
            bar.open = item["open"].get<double>();
            bar.high = item["high"].get<double>();
            bar.low = item["low"].get<double>();
            bar.close = item["close"].get<double>();
            bar.volume = item.value("tick_volume", 0);
            bar.tick_volume = item.value("tick_volume", 0);
            bar.spread = item.value("spread", 0.0);
            bar.source = "mt5";
            bar.quality_score = 1.0;  // native XAU/USD

            result.bars.push_back(bar);
        }

        result.success = true;

    } catch (const std::exception& e) {
        // Graceful degradation: domdata CLI not available or failed
        result.error = std::string("domdata error: ") + e.what();
        result.success = false;
    }

    auto end = std::chrono::steady_clock::now();
    result.latency_ms = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();

    return result;
}

} // namespace dominion
