#pragma once

#include <string>
#include <vector>
#include <memory>
#include <atomic>
#include <functional>
#include <unordered_map>

namespace arrow {
    class Table;
}

namespace dominion {

struct ProgressState {
    std::atomic<size_t> completed_families{0};
    std::atomic<size_t> completed_features{0};
    std::atomic<size_t> total_families{0};
    std::atomic<size_t> total_features{0};
    std::atomic<double> progress_pct{0.0};
    std::atomic<bool> building{false};

    void update_progress();
    std::string format_progress() const;
};

struct DatasetConfig {
    std::string input_path;
    std::string output_path;
    std::string manifest_path;
    size_t max_rows = 0;  // 0 = all
    int num_threads = -1;  // -1 = auto
    bool skip_validation = false;
    bool verbose = true;
};

class DatasetBuilderV2 {
public:
    DatasetBuilderV2(const DatasetConfig& config);
    ~DatasetBuilderV2();

    // Build dataset
    bool build();

    // Progress tracking
    const ProgressState& get_progress() const { return progress_; }

private:
    DatasetConfig config_;
    ProgressState progress_;

    // Data holders
    struct RawData {
        std::vector<int64_t> timestamps;
        std::vector<float> open;
        std::vector<float> high;
        std::vector<float> low;
        std::vector<float> close;
        std::vector<float> tick_volume;
        std::vector<float> spread;
        size_t num_rows = 0;
    };

    std::unique_ptr<RawData> raw_data_;
    std::unordered_map<std::string, std::vector<float>> all_features_;
    std::shared_ptr<arrow::Table> result_table_;

    // Build stages
    bool load_spine();
    bool build_features();
    bool merge_features();
    bool add_targets();
    bool validate();
    bool save_output();

    // Feature families (parallel) - now write to all_features_ map
    void build_return_features();
    void build_volatility_features();
    void build_trend_features();
    void build_session_features();
    void build_micro_features();

    // Helpers
    void log(const std::string& msg);
    void update_progress_bar();
};

// Standalone progress monitor (runs in separate thread)
void monitor_progress(const ProgressState& progress, bool* running);

} // namespace dominion
