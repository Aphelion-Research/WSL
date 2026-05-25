#include "dominion/types.hpp"
#include <iostream>
#include <fstream>
#include <filesystem>
#include <chrono>
#include <thread>
#include <unordered_set>
#include <deque>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

namespace dominion {

// TODO: Replace with actual MT5 API bindings
// For now: stub that would call MT5 native API (MetaTrader5 C++ SDK or Wine bridge)

struct TickKey {
    int64_t time_msc;
    double bid;
    double ask;

    bool operator==(const TickKey& other) const {
        return time_msc == other.time_msc && bid == other.bid && ask == other.ask;
    }
};

struct TickKeyHash {
    std::size_t operator()(const TickKey& k) const {
        return std::hash<int64_t>()(k.time_msc) ^
               (std::hash<double>()(k.bid) << 1) ^
               (std::hash<double>()(k.ask) << 2);
    }
};

class MT5Collector {
public:
    explicit MT5Collector(const std::string& symbol,
                          const std::filesystem::path& out_root,
                          int tick_interval_ms = 250,
                          int bar_interval_sec = 10,
                          int heartbeat_sec = 10,
                          int max_runtime_sec = 0)
        : symbol_(symbol),
          out_root_(out_root),
          tick_interval_ms_(tick_interval_ms),
          bar_interval_sec_(bar_interval_sec),
          heartbeat_sec_(heartbeat_sec),
          max_runtime_sec_(max_runtime_sec) {}

    void run() {
        std::cout << "MT5 Collector starting...\n";
        std::cout << "Symbol: " << symbol_ << "\n";
        std::cout << "Output root: " << out_root_ << "\n";

        auto start_time = std::chrono::steady_clock::now();

        // TODO: Initialize MT5 connection
        // bool connected = mt5_init();
        // if (!connected) {
        //     std::cerr << "Failed to connect to MT5\n";
        //     return;
        // }

        // TODO: Select symbol
        // bool selected = mt5_select_symbol(symbol_);

        while (true) {
            auto now = std::chrono::steady_clock::now();
            auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(now - start_time).count();

            if (max_runtime_sec_ > 0 && elapsed >= max_runtime_sec_ * 1000) {
                std::cout << "Max runtime reached, stopping...\n";
                break;
            }

            // Collect ticks
            if (elapsed % tick_interval_ms_ == 0) {
                collect_tick();
            }

            // Collect bars
            if (elapsed % (bar_interval_sec_ * 1000) == 0) {
                collect_bar();
            }

            // Heartbeat
            if (elapsed % (heartbeat_sec_ * 1000) == 0) {
                write_heartbeat();
            }

            std::this_thread::sleep_for(std::chrono::milliseconds(tick_interval_ms_));
        }

        // TODO: Shutdown MT5
        // mt5_shutdown();
    }

private:
    void collect_tick() {
        // TODO: Call mt5.symbol_info_tick(symbol_)
        // For now: stub
        Tick tick;
        tick.time_msc = std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::system_clock::now().time_since_epoch()).count();
        tick.bid = 2650.0;  // placeholder
        tick.ask = 2650.5;
        tick.mid = (tick.bid + tick.ask) / 2.0;
        tick.spread = tick.ask - tick.bid;
        tick.flags = 0;
        tick.volume = 100;
        tick.volume_real = 100;
        tick.collected_at = std::chrono::system_clock::now();

        // Dedup
        TickKey key{tick.time_msc, tick.bid, tick.ask};
        if (recent_ticks_.find(key) != recent_ticks_.end()) {
            return;  // duplicate
        }

        recent_ticks_.insert(key);
        if (recent_ticks_.size() > 2000) {
            // TODO: Remove oldest (need ordered structure)
        }

        // Write to JSONL
        write_tick(tick);
        tick_count_++;
    }

    void collect_bar() {
        // TODO: Call mt5.copy_rates_from_pos(symbol_, TIMEFRAME_M1, 0, 2)
        // For now: stub
        Bar bar;
        bar.timestamp = std::chrono::system_clock::now();
        bar.open = 2649.0;
        bar.high = 2651.0;
        bar.low = 2648.0;
        bar.close = 2650.0;
        bar.volume = 10000;
        bar.tick_volume = 100;
        bar.spread = 0.5;
        bar.source = "mt5";

        write_bar(bar);
        bar_count_++;
    }

    void write_tick(const Tick& tick) {
        auto path = get_path("ticks", tick.collected_at);
        std::ofstream ofs(path, std::ios::app);

        json j = {
            {"source", "mt5_combat"},
            {"symbol", symbol_},
            {"time", tick.time_msc / 1000},
            {"time_msc", tick.time_msc},
            {"bid", tick.bid},
            {"ask", tick.ask},
            {"mid", tick.mid},
            {"spread", tick.spread},
            {"flags", tick.flags},
            {"volume", tick.volume},
            {"volume_real", tick.volume_real},
            {"collected_at_utc", iso8601(tick.collected_at)}
        };

        ofs << j.dump() << "\n";
    }

    void write_bar(const Bar& bar) {
        auto path = get_path("bars", bar.timestamp, "M1");
        std::ofstream ofs(path, std::ios::app);

        json j = {
            {"source", "mt5_combat"},
            {"symbol", symbol_},
            {"timeframe", "M1"},
            {"time", std::chrono::duration_cast<std::chrono::seconds>(bar.timestamp.time_since_epoch()).count()},
            {"open", bar.open},
            {"high", bar.high},
            {"low", bar.low},
            {"close", bar.close},
            {"tick_volume", bar.tick_volume},
            {"spread", bar.spread},
            {"real_volume", bar.volume},
            {"collected_at_utc", iso8601(std::chrono::system_clock::now())}
        };

        ofs << j.dump() << "\n";
    }

    void write_heartbeat() {
        auto now = std::chrono::system_clock::now();
        auto path = get_path("health", now);
        std::ofstream ofs(path, std::ios::app);

        json j = {
            {"collected_at_utc", iso8601(now)},
            {"mt5_connected", true},  // TODO: actual status
            {"account_login_masked", "XX***YY"},
            {"symbol_selected", true},
            {"last_tick_age_ms", 0},
            {"tick_count_written", tick_count_},
            {"bar_count_written", bar_count_},
            {"errors_count", 0},
            {"process_pid", getpid()}
        };

        ofs << j.dump() << "\n";
    }

    std::filesystem::path get_path(const std::string& kind,
                                    const Timestamp& ts,
                                    const std::string& timeframe = "") {
        auto ts_t = std::chrono::system_clock::to_time_t(ts);
        std::tm* tm = std::gmtime(&ts_t);

        char date[16], hour[8];
        std::strftime(date, sizeof(date), "%Y-%m-%d", tm);
        std::snprintf(hour, sizeof(hour), "%02d", tm->tm_hour);

        std::filesystem::path dir = out_root_ / symbol_;
        if (timeframe.empty()) {
            dir = dir / kind / ("date=" + std::string(date));
        } else {
            dir = dir / kind / ("timeframe=" + timeframe) / ("date=" + std::string(date));
        }

        std::filesystem::create_directories(dir);
        return dir / (kind + "-" + std::string(hour) + ".jsonl");
    }

    std::string iso8601(const Timestamp& ts) {
        auto ts_t = std::chrono::system_clock::to_time_t(ts);
        auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
            ts.time_since_epoch()) % 1000;

        char buf[64];
        std::strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%S", std::gmtime(&ts_t));
        std::snprintf(buf + std::strlen(buf), sizeof(buf) - std::strlen(buf),
                     ".%03ldZ", ms.count());
        return buf;
    }

    std::string symbol_;
    std::filesystem::path out_root_;
    int tick_interval_ms_;
    int bar_interval_sec_;
    int heartbeat_sec_;
    int max_runtime_sec_;

    std::unordered_set<TickKey, TickKeyHash> recent_ticks_;
    int tick_count_ = 0;
    int bar_count_ = 0;
};

} // namespace dominion
