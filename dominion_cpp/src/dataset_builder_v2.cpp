#include "dominion/dataset_builder_v2.hpp"
#include <parquet/arrow/reader.h>
#include <parquet/arrow/writer.h>
#include <arrow/io/file.h>
#include <arrow/table.h>
#include <arrow/array.h>
#include <arrow/builder.h>
#include <arrow/compute/api.h>
#include <omp.h>
#include <cmath>
#include <algorithm>
#include <iostream>
#include <iomanip>
#include <sstream>
#include <chrono>
#include <thread>
#include <numeric>

namespace dominion {

// Progress formatting
void ProgressState::update_progress() {
    if (total_features > 0) {
        progress_pct.store(100.0 * completed_features.load() / total_features.load());
    }
}

std::string ProgressState::format_progress() const {
    std::ostringstream oss;
    double pct = progress_pct.load();
    size_t completed = completed_features.load();
    size_t total = total_features.load();
    size_t fam_done = completed_families.load();
    size_t fam_total = total_families.load();

    // Progress bar
    int bar_width = 50;
    int filled = static_cast<int>(pct / 100.0 * bar_width);

    oss << "\r[";
    for (int i = 0; i < bar_width; ++i) {
        if (i < filled) oss << "█";
        else if (i == filled) oss << "▓";
        else oss << "░";
    }
    oss << "] ";
    oss << std::fixed << std::setprecision(1) << pct << "% ";
    oss << "(" << completed << "/" << total << " features) ";
    oss << "Family " << fam_done << "/" << fam_total;
    oss << std::flush;

    return oss.str();
}

// Constructor
DatasetBuilderV2::DatasetBuilderV2(const DatasetConfig& config)
    : config_(config) {

    if (config_.num_threads < 0) {
        config_.num_threads = omp_get_max_threads();
    }
    omp_set_num_threads(config_.num_threads);

    log("Initialized C++ Dataset Builder v2");
    log("Threads: " + std::to_string(config_.num_threads));
}

DatasetBuilderV2::~DatasetBuilderV2() = default;

void DatasetBuilderV2::log(const std::string& msg) {
    if (config_.verbose) {
        auto now = std::chrono::system_clock::now();
        auto time_t = std::chrono::system_clock::to_time_t(now);
        std::cout << "[" << std::put_time(std::localtime(&time_t), "%H:%M:%S") << "] " << msg << std::endl;
    }
}

// Main build
bool DatasetBuilderV2::build() {
    progress_.building.store(true);

    log("========================================");
    log("HYDRA C++ Dataset Builder v2");
    log("========================================");

    // Stage 1: Load spine
    log("[1/6] Loading spine data...");
    if (!load_spine()) {
        log("ERROR: Failed to load spine");
        return false;
    }
    log("  Loaded " + std::to_string(raw_data_->num_rows) + " rows");

    // Stage 2: Build features (massively parallel)
    log("[2/6] Building features (parallel)...");
    progress_.total_families.store(5);  // Return, Vol, Trend, Session, Micro

    // Total: 194 + 172 + 169 + 47 + 59 = 641 base features
    progress_.total_features.store(1870);

    if (!build_features()) {
        log("ERROR: Failed to build features");
        return false;
    }

    // Stage 3: Merge with result
    log("[3/6] Merging features into dataset...");
    if (!merge_features()) {
        log("ERROR: Failed to merge features");
        return false;
    }

    // Stage 4: Add targets
    log("[4/6] Adding target labels...");
    if (!add_targets()) {
        log("ERROR: Failed to add targets");
        return false;
    }

    // Stage 5: Validate
    if (!config_.skip_validation) {
        log("[5/6] Validating...");
        if (!validate()) {
            log("WARNING: Validation issues found");
        }
    } else {
        log("[5/6] Validation SKIPPED");
    }

    // Stage 6: Save
    log("[6/6] Saving to parquet...");
    if (!save_output()) {
        log("ERROR: Failed to save output");
        return false;
    }

    progress_.building.store(false);
    log("========================================");
    log("BUILD COMPLETE");
    log("Output: " + config_.output_path);
    log("========================================");

    return true;
}

// Load spine (Arrow/Parquet)
bool DatasetBuilderV2::load_spine() {
    try {
        std::shared_ptr<arrow::io::ReadableFile> infile;
        PARQUET_ASSIGN_OR_THROW(infile, arrow::io::ReadableFile::Open(config_.input_path));

        std::unique_ptr<parquet::arrow::FileReader> reader;
        auto open_result = parquet::arrow::OpenFile(infile, arrow::default_memory_pool());
        if (!open_result.ok()) {
            log("ERROR: Failed to open parquet file");
            return false;
        }
        reader = std::move(open_result).ValueOrDie();

        std::shared_ptr<arrow::Table> table;
        PARQUET_THROW_NOT_OK(reader->ReadTable(&table));

        raw_data_ = std::make_unique<RawData>();

        // Extract columns
        auto get_col = [&](const std::string& name) -> std::shared_ptr<arrow::Array> {
            auto col_idx = table->schema()->GetFieldIndex(name);
            if (col_idx < 0) return nullptr;
            return table->column(col_idx)->chunk(0);
        };

        auto time_array = std::static_pointer_cast<arrow::TimestampArray>(get_col("time"));
        auto open_array = std::static_pointer_cast<arrow::FloatArray>(get_col("open"));
        auto high_array = std::static_pointer_cast<arrow::FloatArray>(get_col("high"));
        auto low_array = std::static_pointer_cast<arrow::FloatArray>(get_col("low"));
        auto close_array = std::static_pointer_cast<arrow::FloatArray>(get_col("close"));
        auto tick_vol_array = std::static_pointer_cast<arrow::FloatArray>(get_col("tick_volume"));
        auto spread_array = std::static_pointer_cast<arrow::FloatArray>(get_col("spread"));

        size_t n = config_.max_rows > 0 ? std::min<size_t>(config_.max_rows, table->num_rows()) : table->num_rows();
        raw_data_->num_rows = n;

        raw_data_->timestamps.resize(n);
        raw_data_->open.resize(n);
        raw_data_->high.resize(n);
        raw_data_->low.resize(n);
        raw_data_->close.resize(n);
        raw_data_->tick_volume.resize(n);
        raw_data_->spread.resize(n);

        #pragma omp parallel for
        for (size_t i = 0; i < n; ++i) {
            raw_data_->timestamps[i] = time_array->Value(i);
            raw_data_->open[i] = open_array->IsNull(i) ? NAN : open_array->Value(i);
            raw_data_->high[i] = high_array->IsNull(i) ? NAN : high_array->Value(i);
            raw_data_->low[i] = low_array->IsNull(i) ? NAN : low_array->Value(i);
            raw_data_->close[i] = close_array->IsNull(i) ? NAN : close_array->Value(i);
            raw_data_->tick_volume[i] = tick_vol_array->IsNull(i) ? NAN : tick_vol_array->Value(i);
            raw_data_->spread[i] = spread_array->IsNull(i) ? NAN : spread_array->Value(i);
        }

        return true;
    } catch (const std::exception& e) {
        log("ERROR loading spine: " + std::string(e.what()));
        return false;
    }
}

// Helpers for rolling operations (optimized, single-pass)
inline void rolling_mean_std(const std::vector<float>& src, int window, std::vector<float>& mean, std::vector<float>& std_dev) {
    size_t n = src.size();
    mean.resize(n);
    std_dev.resize(n);

    #pragma omp parallel for schedule(dynamic, 1024)
    for (size_t i = 0; i < n; ++i) {
        if (i + 1 < static_cast<size_t>(window)) {
            mean[i] = NAN;
            std_dev[i] = NAN;
            continue;
        }

        double sum = 0.0, sum_sq = 0.0;
        int count = 0;
        for (int j = 0; j < window; ++j) {
            size_t idx = i - j;
            if (!std::isnan(src[idx])) {
                sum += src[idx];
                sum_sq += src[idx] * src[idx];
                count++;
            }
        }

        if (count > 1) {
            mean[i] = static_cast<float>(sum / count);
            double var = (sum_sq / count) - (mean[i] * mean[i]);
            std_dev[i] = static_cast<float>(std::sqrt(std::max(0.0, var)));
        } else {
            mean[i] = NAN;
            std_dev[i] = NAN;
        }
    }
}

inline void rolling_sum(const std::vector<float>& src, int window, std::vector<float>& out) {
    size_t n = src.size();
    out.resize(n);

    #pragma omp parallel for schedule(dynamic, 1024)
    for (size_t i = 0; i < n; ++i) {
        if (i + 1 < static_cast<size_t>(window)) {
            out[i] = NAN;
            continue;
        }

        double sum = 0.0;
        int count = 0;
        for (int j = 0; j < window; ++j) {
            if (!std::isnan(src[i - j])) {
                sum += src[i - j];
                count++;
            }
        }
        out[i] = count > 0 ? static_cast<float>(sum) : NAN;
    }
}

inline void rolling_max_min(const std::vector<float>& src, int window, std::vector<float>& max_out, std::vector<float>& min_out) {
    size_t n = src.size();
    max_out.resize(n);
    min_out.resize(n);

    #pragma omp parallel for schedule(dynamic, 1024)
    for (size_t i = 0; i < n; ++i) {
        if (i + 1 < static_cast<size_t>(window)) {
            max_out[i] = NAN;
            min_out[i] = NAN;
            continue;
        }

        float max_val = -std::numeric_limits<float>::infinity();
        float min_val = std::numeric_limits<float>::infinity();
        for (int j = 0; j < window; ++j) {
            if (!std::isnan(src[i - j])) {
                max_val = std::max(max_val, src[i - j]);
                min_val = std::min(min_val, src[i - j]);
            }
        }
        max_out[i] = std::isfinite(max_val) ? max_val : NAN;
        min_out[i] = std::isfinite(min_val) ? min_val : NAN;
    }
}

// Feature builders (FULL EXPANSION)
bool DatasetBuilderV2::build_features() {
    all_features_.clear();

    // Launch family builders in parallel
    #pragma omp parallel sections
    {
        #pragma omp section
        {
            build_return_features();
            progress_.completed_families.fetch_add(1);
        }

        #pragma omp section
        {
            build_volatility_features();
            progress_.completed_families.fetch_add(1);
        }

        #pragma omp section
        {
            build_trend_features();
            progress_.completed_families.fetch_add(1);
        }

        #pragma omp section
        {
            build_session_features();
            progress_.completed_families.fetch_add(1);
        }

        #pragma omp section
        {
            build_micro_features();
            progress_.completed_families.fetch_add(1);
        }
    }

    return true;
}

// RETURN FEATURES (massive expansion → ~400 features)
void DatasetBuilderV2::build_return_features() {
    size_t n = raw_data_->num_rows;
    const auto& close = raw_data_->close;

    // Pre-compute log close
    std::vector<float> log_close(n);
    #pragma omp parallel for
    for (size_t i = 0; i < n; ++i) {
        log_close[i] = std::isnan(close[i]) ? NAN : std::log(close[i]);
    }

    // Horizons (16 horizons)
    std::vector<int> horizons = {1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 288, 377, 610, 987};

    // 1. Log/pct returns: 16×2 = 32
    #pragma omp parallel for schedule(dynamic)
    for (size_t h_idx = 0; h_idx < horizons.size(); ++h_idx) {
        int h = horizons[h_idx];

        std::vector<float> log_ret(n), pct_ret(n);
        for (size_t i = 0; i < n; ++i) {
            if (i > static_cast<size_t>(h) && !std::isnan(log_close[i-1]) && !std::isnan(log_close[i-h-1])) {
                log_ret[i] = log_close[i-1] - log_close[i-h-1];
                pct_ret[i] = (close[i-1] - close[i-h-1]) / close[i-h-1];
            } else {
                log_ret[i] = NAN;
                pct_ret[i] = NAN;
            }
        }

        #pragma omp critical
        {
            all_features_["log_ret_" + std::to_string(h) + "b"] = log_ret;
            all_features_["pct_ret_" + std::to_string(h) + "b"] = pct_ret;
        }
        progress_.completed_features.fetch_add(2);
        progress_.update_progress();
    }

    // 2. 1-bar log return for downstream
    std::vector<float> log_ret_1(n);
    for (size_t i = 1; i < n; ++i) {
        log_ret_1[i] = std::isnan(log_close[i-1]) || std::isnan(log_close[i-2]) ? NAN : log_close[i-1] - log_close[i-2];
    }

    // 3. Cumulative returns: 12 windows = 12
    std::vector<int> cum_windows = {5, 10, 20, 30, 60, 90, 120, 180, 240, 288, 360, 480};
    #pragma omp parallel for schedule(dynamic)
    for (size_t w_idx = 0; w_idx < cum_windows.size(); ++w_idx) {
        int w = cum_windows[w_idx];
        std::vector<float> cum;
        rolling_sum(log_ret_1, w, cum);

        #pragma omp critical
        {
            all_features_["cum_ret_" + std::to_string(w) + "b"] = cum;
        }
        progress_.completed_features.fetch_add(1);
        progress_.update_progress();
    }

    // 4. Return z-scores: 10 windows = 10
    std::vector<int> z_windows = {10, 20, 30, 60, 90, 144, 200, 288, 400, 576};
    #pragma omp parallel for schedule(dynamic)
    for (size_t w_idx = 0; w_idx < z_windows.size(); ++w_idx) {
        int w = z_windows[w_idx];
        std::vector<float> mean, std_dev;
        rolling_mean_std(log_ret_1, w, mean, std_dev);

        std::vector<float> z(n);
        for (size_t i = 0; i < n; ++i) {
            if (!std::isnan(mean[i]) && std_dev[i] > 1e-10) {
                z[i] = (log_ret_1[i] - mean[i]) / std_dev[i];
            } else {
                z[i] = NAN;
            }
        }

        #pragma omp critical
        {
            all_features_["ret_zscore_" + std::to_string(w) + "b"] = z;
        }
        progress_.completed_features.fetch_add(1);
        progress_.update_progress();
    }

    // 5. Return ranks/percentiles: 7 windows × 3 = 21
    std::vector<int> pct_windows = {30, 60, 90, 144, 200, 288, 400};
    #pragma omp parallel for schedule(dynamic)
    for (size_t w_idx = 0; w_idx < pct_windows.size(); ++w_idx) {
        int w = pct_windows[w_idx];

        std::vector<float> rank(n), pct25(n), pct75(n);
        for (size_t i = 0; i < n; ++i) {
            if (i + 1 < static_cast<size_t>(w)) {
                rank[i] = pct25[i] = pct75[i] = NAN;
                continue;
            }

            std::vector<float> window_vals;
            for (int j = 0; j < w; ++j) {
                if (!std::isnan(log_ret_1[i - j])) {
                    window_vals.push_back(log_ret_1[i - j]);
                }
            }

            if (window_vals.size() > 5) {
                std::sort(window_vals.begin(), window_vals.end());
                rank[i] = window_vals[window_vals.size() / 2];
                pct25[i] = window_vals[window_vals.size() / 4];
                pct75[i] = window_vals[window_vals.size() * 3 / 4];
            } else {
                rank[i] = pct25[i] = pct75[i] = NAN;
            }
        }

        #pragma omp critical
        {
            all_features_["ret_rank_" + std::to_string(w) + "b"] = rank;
            all_features_["ret_pct25_" + std::to_string(w) + "b"] = pct25;
            all_features_["ret_pct75_" + std::to_string(w) + "b"] = pct75;
        }
        progress_.completed_features.fetch_add(3);
        progress_.update_progress();
    }

    // 6. Return acceleration/jerk/snap: 9 horizons × 3 = 27
    std::vector<int> accel_horizons = {1, 3, 5, 8, 13, 21, 34, 55, 89};
    #pragma omp parallel for schedule(dynamic)
    for (size_t h_idx = 0; h_idx < accel_horizons.size(); ++h_idx) {
        int h = accel_horizons[h_idx];

        std::vector<float> ret(n), accel(n), jerk(n), snap(n);
        for (size_t i = 0; i < n; ++i) {
            if (i > static_cast<size_t>(h) && !std::isnan(log_close[i-1]) && !std::isnan(log_close[i-h-1])) {
                ret[i] = log_close[i-1] - log_close[i-h-1];
            } else {
                ret[i] = NAN;
            }
        }

        for (size_t i = 1; i < n; ++i) {
            accel[i] = std::isnan(ret[i]) || std::isnan(ret[i-1]) ? NAN : ret[i] - ret[i-1];
        }
        for (size_t i = 1; i < n; ++i) {
            jerk[i] = std::isnan(accel[i]) || std::isnan(accel[i-1]) ? NAN : accel[i] - accel[i-1];
        }
        for (size_t i = 1; i < n; ++i) {
            snap[i] = std::isnan(jerk[i]) || std::isnan(jerk[i-1]) ? NAN : jerk[i] - jerk[i-1];
        }

        #pragma omp critical
        {
            all_features_["ret_accel_" + std::to_string(h) + "b"] = accel;
            all_features_["ret_jerk_" + std::to_string(h) + "b"] = jerk;
            all_features_["ret_snap_" + std::to_string(h) + "b"] = snap;
        }
        progress_.completed_features.fetch_add(3);
        progress_.update_progress();
    }

    // 7. Signed persistence: 9 windows × 2 = 18
    std::vector<float> sign(n);
    for (size_t i = 0; i < n; ++i) {
        sign[i] = log_ret_1[i] > 0 ? 1.0f : (log_ret_1[i] < 0 ? -1.0f : 0.0f);
    }

    std::vector<int> persist_windows = {5, 10, 15, 20, 30, 40, 60, 90, 120};
    #pragma omp parallel for schedule(dynamic)
    for (size_t w_idx = 0; w_idx < persist_windows.size(); ++w_idx) {
        int w = persist_windows[w_idx];

        std::vector<float> mean(n), std_dev(n), sum;
        rolling_mean_std(sign, w, mean, std_dev);
        rolling_sum(sign, w, sum);

        #pragma omp critical
        {
            all_features_["ret_persist_" + std::to_string(w) + "b"] = mean;
            all_features_["ret_streak_" + std::to_string(w) + "b"] = sum;
        }
        progress_.completed_features.fetch_add(2);
        progress_.update_progress();
    }

    // 8. Mean reversion: 11 windows × 2 = 22
    std::vector<int> mean_rev_windows = {10, 20, 30, 40, 60, 90, 120, 144, 200, 288, 400};
    #pragma omp parallel for schedule(dynamic)
    for (size_t w_idx = 0; w_idx < mean_rev_windows.size(); ++w_idx) {
        int w = mean_rev_windows[w_idx];

        std::vector<float> mean, std_dev;
        std::vector<float> close_lag(n);
        for (size_t i = 1; i < n; ++i) {
            close_lag[i] = close[i-1];
        }

        rolling_mean_std(close_lag, w, mean, std_dev);

        std::vector<float> mean_rev(n), mean_rev_z(n);
        for (size_t i = 0; i < n; ++i) {
            if (!std::isnan(mean[i]) && mean[i] > 1e-10) {
                mean_rev[i] = (close_lag[i] - mean[i]) / mean[i];
                if (std_dev[i] > 1e-10) {
                    mean_rev_z[i] = (close_lag[i] - mean[i]) / std_dev[i];
                } else {
                    mean_rev_z[i] = NAN;
                }
            } else {
                mean_rev[i] = mean_rev_z[i] = NAN;
            }
        }

        #pragma omp critical
        {
            all_features_["mean_rev_" + std::to_string(w) + "b"] = mean_rev;
            all_features_["mean_rev_z_" + std::to_string(w) + "b"] = mean_rev_z;
        }
        progress_.completed_features.fetch_add(2);
        progress_.update_progress();
    }

    // 9. Drawdown/drawup: 13 windows × 4 = 52
    std::vector<int> dd_windows = {5, 10, 20, 30, 40, 60, 90, 120, 144, 200, 288, 400, 576};
    #pragma omp parallel for schedule(dynamic)
    for (size_t w_idx = 0; w_idx < dd_windows.size(); ++w_idx) {
        int w = dd_windows[w_idx];

        std::vector<float> max_val, min_val;
        std::vector<float> close_lag(n);
        for (size_t i = 1; i < n; ++i) {
            close_lag[i] = close[i-1];
        }

        rolling_max_min(close_lag, w, max_val, min_val);

        std::vector<float> dd(n), du(n), dist_high(n), dist_low(n);
        for (size_t i = 0; i < n; ++i) {
            if (!std::isnan(max_val[i]) && max_val[i] > 1e-10) {
                dd[i] = (close_lag[i] - max_val[i]) / max_val[i];
                dist_high[i] = (max_val[i] - close_lag[i]) / close_lag[i];
            } else {
                dd[i] = dist_high[i] = NAN;
            }

            if (!std::isnan(min_val[i]) && min_val[i] > 1e-10 && close_lag[i] > 1e-10) {
                du[i] = (close_lag[i] - min_val[i]) / min_val[i];
                dist_low[i] = (close_lag[i] - min_val[i]) / close_lag[i];
            } else {
                du[i] = dist_low[i] = NAN;
            }
        }

        #pragma omp critical
        {
            all_features_["dd_" + std::to_string(w) + "b"] = dd;
            all_features_["du_" + std::to_string(w) + "b"] = du;
            all_features_["dist_to_high_" + std::to_string(w) + "b"] = dist_high;
            all_features_["dist_to_low_" + std::to_string(w) + "b"] = dist_low;
        }
        progress_.completed_features.fetch_add(4);
        progress_.update_progress();
    }
}

// VOLATILITY FEATURES (massive expansion → ~350 features)
void DatasetBuilderV2::build_volatility_features() {
    size_t n = raw_data_->num_rows;
    const auto& close = raw_data_->close;
    const auto& high = raw_data_->high;
    const auto& low = raw_data_->low;
    const auto& opn = raw_data_->open;

    // Pre-compute log prices (lagged)
    std::vector<float> log_h(n), log_l(n), log_c(n), log_o(n);
    #pragma omp parallel for
    for (size_t i = 1; i < n; ++i) {
        log_h[i] = std::isnan(high[i-1]) ? NAN : std::log(high[i-1]);
        log_l[i] = std::isnan(low[i-1]) ? NAN : std::log(low[i-1]);
        log_c[i] = std::isnan(close[i-1]) ? NAN : std::log(close[i-1]);
        log_o[i] = std::isnan(opn[i-1]) ? NAN : std::log(opn[i-1]);
    }

    // Pre-compute base series
    std::vector<float> hl2(n), co2(n), hc(n), ho(n), lc(n), lo_val(n);
    #pragma omp parallel for
    for (size_t i = 1; i < n; ++i) {
        hl2[i] = std::pow(log_h[i] - log_l[i], 2);
        co2[i] = std::pow(log_c[i] - log_o[i], 2);
        hc[i] = log_h[i] - log_c[i];
        ho[i] = log_h[i] - log_o[i];
        lc[i] = log_l[i] - log_c[i];
        lo_val[i] = log_l[i] - log_o[i];
    }

    // 1-bar log return
    std::vector<float> log_ret(n);
    for (size_t i = 2; i < n; ++i) {
        log_ret[i] = log_c[i] - log_c[i-1];
    }

    // Windows (23 windows)
    std::vector<int> windows = {5, 8, 10, 14, 20, 30, 34, 40, 55, 60, 72, 89, 100, 120, 144, 200, 233, 288, 377, 480, 576, 720, 987};

    // 1. Realized/Parkinson/GK/RS vol: 23×4 = 92
    #pragma omp parallel for schedule(dynamic)
    for (size_t w_idx = 0; w_idx < windows.size(); ++w_idx) {
        int w = windows[w_idx];

        // Realized
        std::vector<float> rvol(n);
        for (size_t i = 0; i < n; ++i) {
            if (i + 1 < static_cast<size_t>(w)) {
                rvol[i] = NAN;
                continue;
            }
            double sum = 0.0, sum_sq = 0.0;
            int count = 0;
            for (int j = 0; j < w; ++j) {
                if (!std::isnan(log_ret[i - j])) {
                    sum += log_ret[i - j];
                    sum_sq += log_ret[i - j] * log_ret[i - j];
                    count++;
                }
            }
            if (count > 1) {
                double mean = sum / count;
                double var = (sum_sq / count) - mean * mean;
                rvol[i] = std::sqrt(std::max(0.0, var));
            } else {
                rvol[i] = NAN;
            }
        }

        // Parkinson
        std::vector<float> park(n);
        for (size_t i = 0; i < n; ++i) {
            if (i + 1 < static_cast<size_t>(w)) {
                park[i] = NAN;
                continue;
            }
            double sum = 0.0;
            int count = 0;
            for (int j = 0; j < w; ++j) {
                if (!std::isnan(hl2[i - j])) {
                    sum += hl2[i - j];
                    count++;
                }
            }
            if (count > 0) {
                park[i] = std::sqrt(sum / (4 * std::log(2.0) * count));
            } else {
                park[i] = NAN;
            }
        }

        // Garman-Klass
        std::vector<float> gk(n);
        for (size_t i = 0; i < n; ++i) {
            if (i + 1 < static_cast<size_t>(w)) {
                gk[i] = NAN;
                continue;
            }
            double sum = 0.0;
            int count = 0;
            for (int j = 0; j < w; ++j) {
                if (!std::isnan(hl2[i - j]) && !std::isnan(co2[i - j])) {
                    double gk_val = 0.5 * hl2[i - j] - (2 * std::log(2.0) - 1) * co2[i - j];
                    sum += std::abs(gk_val);
                    count++;
                }
            }
            if (count > 0) {
                gk[i] = std::sqrt(sum / count);
            } else {
                gk[i] = NAN;
            }
        }

        // Rogers-Satchell
        std::vector<float> rs(n);
        for (size_t i = 0; i < n; ++i) {
            if (i + 1 < static_cast<size_t>(w)) {
                rs[i] = NAN;
                continue;
            }
            double sum = 0.0;
            int count = 0;
            for (int j = 0; j < w; ++j) {
                if (!std::isnan(hc[i - j]) && !std::isnan(ho[i - j]) && !std::isnan(lc[i - j]) && !std::isnan(lo_val[i - j])) {
                    double rs_val = hc[i - j] * ho[i - j] + lc[i - j] * lo_val[i - j];
                    sum += std::abs(rs_val);
                    count++;
                }
            }
            if (count > 0) {
                rs[i] = std::sqrt(sum / count);
            } else {
                rs[i] = NAN;
            }
        }

        #pragma omp critical
        {
            all_features_["rvol_" + std::to_string(w) + "b"] = rvol;
            all_features_["park_vol_" + std::to_string(w) + "b"] = park;
            all_features_["gk_vol_" + std::to_string(w) + "b"] = gk;
            all_features_["rs_vol_" + std::to_string(w) + "b"] = rs;
        }
        progress_.completed_features.fetch_add(4);
        progress_.update_progress();
    }

    // 2. EWMA vol: 12 spans = 12
    std::vector<int> ewma_spans = {5, 10, 15, 20, 30, 40, 60, 90, 120, 144, 200, 288};
    #pragma omp parallel for schedule(dynamic)
    for (size_t span_idx = 0; span_idx < ewma_spans.size(); ++span_idx) {
        int span = ewma_spans[span_idx];
        double alpha = 2.0 / (span + 1);

        std::vector<float> ewma(n);
        double ewma_val = 0.0;
        for (size_t i = 1; i < n; ++i) {
            if (!std::isnan(log_ret[i]) && i > 1) {
                double ret_sq = log_ret[i] * log_ret[i];
                ewma_val = alpha * ret_sq + (1 - alpha) * ewma_val;
                ewma[i] = std::sqrt(ewma_val);
            } else {
                ewma[i] = NAN;
            }
        }

        #pragma omp critical
        {
            all_features_["ewma_vol_" + std::to_string(span) + "b"] = ewma;
        }
        progress_.completed_features.fetch_add(1);
        progress_.update_progress();
    }

    // 3. Vol z-scores + percentiles: 9 windows × 4 = 36
    std::vector<int> vol_stat_windows = {10, 20, 30, 60, 90, 144, 200, 288, 400};
    #pragma omp parallel for schedule(dynamic)
    for (size_t w_idx = 0; w_idx < vol_stat_windows.size(); ++w_idx) {
        int w = vol_stat_windows[w_idx];

        // First compute vol
        std::vector<float> vol(n);
        for (size_t i = 0; i < n; ++i) {
            if (i + 1 < static_cast<size_t>(w)) {
                vol[i] = NAN;
                continue;
            }
            double sum = 0.0, sum_sq = 0.0;
            int count = 0;
            for (int j = 0; j < w; ++j) {
                if (!std::isnan(log_ret[i - j])) {
                    sum += log_ret[i - j];
                    sum_sq += log_ret[i - j] * log_ret[i - j];
                    count++;
                }
            }
            if (count > 1) {
                double mean = sum / count;
                double var = (sum_sq / count) - mean * mean;
                vol[i] = std::sqrt(std::max(0.0, var));
            } else {
                vol[i] = NAN;
            }
        }

        // Vol mean/std
        std::vector<float> vol_mean, vol_std;
        rolling_mean_std(vol, w, vol_mean, vol_std);

        std::vector<float> vol_z(n), rank(n), pct25(n), pct75(n);
        for (size_t i = 0; i < n; ++i) {
            if (!std::isnan(vol_mean[i]) && vol_std[i] > 1e-10) {
                vol_z[i] = (vol[i] - vol_mean[i]) / vol_std[i];
            } else {
                vol_z[i] = NAN;
            }

            // Percentiles
            if (i + 1 < static_cast<size_t>(w)) {
                rank[i] = pct25[i] = pct75[i] = NAN;
                continue;
            }

            std::vector<float> window_vals;
            for (int j = 0; j < w; ++j) {
                if (!std::isnan(vol[i - j])) {
                    window_vals.push_back(vol[i - j]);
                }
            }

            if (window_vals.size() > 5) {
                std::sort(window_vals.begin(), window_vals.end());
                rank[i] = window_vals[window_vals.size() / 2];
                pct25[i] = window_vals[window_vals.size() / 4];
                pct75[i] = window_vals[window_vals.size() * 3 / 4];
            } else {
                rank[i] = pct25[i] = pct75[i] = NAN;
            }
        }

        #pragma omp critical
        {
            all_features_["vol_zscore_" + std::to_string(w) + "b"] = vol_z;
            all_features_["vol_rank_" + std::to_string(w) + "b"] = rank;
            all_features_["vol_pct25_" + std::to_string(w) + "b"] = pct25;
            all_features_["vol_pct75_" + std::to_string(w) + "b"] = pct75;
        }
        progress_.completed_features.fetch_add(4);
        progress_.update_progress();
    }

    // 4. Vol-of-vol: 8 windows = 8
    std::vector<int> vov_windows = {10, 20, 30, 60, 90, 120, 144, 200};
    #pragma omp parallel for schedule(dynamic)
    for (size_t w_idx = 0; w_idx < vov_windows.size(); ++w_idx) {
        int w = vov_windows[w_idx];

        // Compute 20-bar vol
        std::vector<float> vol_20(n);
        for (size_t i = 0; i < n; ++i) {
            if (i + 1 < 20) {
                vol_20[i] = NAN;
                continue;
            }
            double sum = 0.0, sum_sq = 0.0;
            int count = 0;
            for (int j = 0; j < 20; ++j) {
                if (!std::isnan(log_ret[i - j])) {
                    sum += log_ret[i - j];
                    sum_sq += log_ret[i - j] * log_ret[i - j];
                    count++;
                }
            }
            if (count > 1) {
                double mean = sum / count;
                double var = (sum_sq / count) - mean * mean;
                vol_20[i] = std::sqrt(std::max(0.0, var));
            } else {
                vol_20[i] = NAN;
            }
        }

        // Vol of vol_20
        std::vector<float> vov(n);
        for (size_t i = 0; i < n; ++i) {
            if (i + 1 < static_cast<size_t>(w)) {
                vov[i] = NAN;
                continue;
            }
            double sum = 0.0, sum_sq = 0.0;
            int count = 0;
            for (int j = 0; j < w; ++j) {
                if (!std::isnan(vol_20[i - j])) {
                    sum += vol_20[i - j];
                    sum_sq += vol_20[i - j] * vol_20[i - j];
                    count++;
                }
            }
            if (count > 1) {
                double mean = sum / count;
                double var = (sum_sq / count) - mean * mean;
                vov[i] = std::sqrt(std::max(0.0, var));
            } else {
                vov[i] = NAN;
            }
        }

        #pragma omp critical
        {
            all_features_["vov_" + std::to_string(w) + "b"] = vov;
        }
        progress_.completed_features.fetch_add(1);
        progress_.update_progress();
    }

    // 5. Vol ratio: 12 pairs = 12
    std::vector<std::pair<int, int>> vol_ratio_pairs = {
        {5, 20}, {5, 60}, {10, 30}, {10, 60}, {10, 144}, {20, 60},
        {20, 144}, {30, 90}, {60, 144}, {60, 288}, {144, 288}, {144, 576}
    };
    #pragma omp parallel for schedule(dynamic)
    for (size_t pair_idx = 0; pair_idx < vol_ratio_pairs.size(); ++pair_idx) {
        int short_w = vol_ratio_pairs[pair_idx].first;
        int long_w = vol_ratio_pairs[pair_idx].second;

        // Compute short vol
        std::vector<float> vol_s(n), vol_l(n);
        for (size_t i = 0; i < n; ++i) {
            if (i + 1 < static_cast<size_t>(short_w)) {
                vol_s[i] = NAN;
            } else {
                double sum = 0.0, sum_sq = 0.0;
                int count = 0;
                for (int j = 0; j < short_w; ++j) {
                    if (!std::isnan(log_ret[i - j])) {
                        sum += log_ret[i - j];
                        sum_sq += log_ret[i - j] * log_ret[i - j];
                        count++;
                    }
                }
                if (count > 1) {
                    double mean = sum / count;
                    double var = (sum_sq / count) - mean * mean;
                    vol_s[i] = std::sqrt(std::max(0.0, var));
                } else {
                    vol_s[i] = NAN;
                }
            }

            if (i + 1 < static_cast<size_t>(long_w)) {
                vol_l[i] = NAN;
            } else {
                double sum = 0.0, sum_sq = 0.0;
                int count = 0;
                for (int j = 0; j < long_w; ++j) {
                    if (!std::isnan(log_ret[i - j])) {
                        sum += log_ret[i - j];
                        sum_sq += log_ret[i - j] * log_ret[i - j];
                        count++;
                    }
                }
                if (count > 1) {
                    double mean = sum / count;
                    double var = (sum_sq / count) - mean * mean;
                    vol_l[i] = std::sqrt(std::max(0.0, var));
                } else {
                    vol_l[i] = NAN;
                }
            }
        }

        std::vector<float> ratio(n);
        for (size_t i = 0; i < n; ++i) {
            if (!std::isnan(vol_s[i]) && vol_l[i] > 1e-10) {
                ratio[i] = vol_s[i] / vol_l[i];
            } else {
                ratio[i] = NAN;
            }
        }

        #pragma omp critical
        {
            all_features_["vol_ratio_" + std::to_string(short_w) + "_" + std::to_string(long_w) + "b"] = ratio;
        }
        progress_.completed_features.fetch_add(1);
        progress_.update_progress();
    }

    // 6. ATR: 10 windows × 2 = 20
    std::vector<float> tr(n);
    #pragma omp parallel for
    for (size_t i = 2; i < n; ++i) {
        float hl = std::abs(high[i-1] - low[i-1]);
        float hc = std::abs(high[i-1] - close[i-2]);
        float lc = std::abs(low[i-1] - close[i-2]);
        tr[i] = std::max({hl, hc, lc});
    }

    size_t atr_count = std::min<size_t>(10, windows.size());
    #pragma omp parallel for schedule(dynamic)
    for (size_t w_idx = 0; w_idx < atr_count; ++w_idx) {
        int w = windows[w_idx];

        std::vector<float> atr(n), atr_pct(n);
        for (size_t i = 0; i < n; ++i) {
            if (i + 1 < static_cast<size_t>(w)) {
                atr[i] = atr_pct[i] = NAN;
                continue;
            }
            double sum = 0.0;
            int count = 0;
            for (int j = 0; j < w; ++j) {
                if (!std::isnan(tr[i - j])) {
                    sum += tr[i - j];
                    count++;
                }
            }
            if (count > 0) {
                atr[i] = sum / count;
                if (!std::isnan(close[i-1]) && close[i-1] > 1e-10) {
                    atr_pct[i] = atr[i] / close[i-1];
                } else {
                    atr_pct[i] = NAN;
                }
            } else {
                atr[i] = atr_pct[i] = NAN;
            }
        }

        #pragma omp critical
        {
            all_features_["atr_" + std::to_string(w) + "b"] = atr;
            all_features_["atr_pct_" + std::to_string(w) + "b"] = atr_pct;
        }
        progress_.completed_features.fetch_add(2);
        progress_.update_progress();
    }

    // 7. Range expansion: 4 windows = 4
    std::vector<int> range_windows = {5, 10, 20, 60};
    #pragma omp parallel for schedule(dynamic)
    for (size_t w_idx = 0; w_idx < range_windows.size(); ++w_idx) {
        int w = range_windows[w_idx];

        std::vector<float> range_now(n);
        for (size_t i = 1; i < n; ++i) {
            range_now[i] = high[i-1] - low[i-1];
        }

        std::vector<float> range_avg(n);
        for (size_t i = 0; i < n; ++i) {
            if (i + 1 < static_cast<size_t>(w)) {
                range_avg[i] = NAN;
                continue;
            }
            double sum = 0.0;
            int count = 0;
            for (int j = 0; j < w; ++j) {
                if (!std::isnan(range_now[i - j])) {
                    sum += range_now[i - j];
                    count++;
                }
            }
            range_avg[i] = count > 0 ? sum / count : NAN;
        }

        std::vector<float> range_exp(n);
        for (size_t i = 0; i < n; ++i) {
            if (!std::isnan(range_avg[i]) && range_avg[i] > 1e-10) {
                range_exp[i] = range_now[i] / range_avg[i];
            } else {
                range_exp[i] = NAN;
            }
        }

        #pragma omp critical
        {
            all_features_["range_exp_" + std::to_string(w) + "b"] = range_exp;
        }
        progress_.completed_features.fetch_add(1);
        progress_.update_progress();
    }

    // 8. Vol slope: 3 windows = 3
    std::vector<int> vol_slope_windows = {20, 60, 144};
    #pragma omp parallel for schedule(dynamic)
    for (size_t w_idx = 0; w_idx < vol_slope_windows.size(); ++w_idx) {
        int w = vol_slope_windows[w_idx];

        // Compute 20-bar vol
        std::vector<float> vol_20(n);
        for (size_t i = 0; i < n; ++i) {
            if (i + 1 < 20) {
                vol_20[i] = NAN;
                continue;
            }
            double sum = 0.0, sum_sq = 0.0;
            int count = 0;
            for (int j = 0; j < 20; ++j) {
                if (!std::isnan(log_ret[i - j])) {
                    sum += log_ret[i - j];
                    sum_sq += log_ret[i - j] * log_ret[i - j];
                    count++;
                }
            }
            if (count > 1) {
                double mean = sum / count;
                double var = (sum_sq / count) - mean * mean;
                vol_20[i] = std::sqrt(std::max(0.0, var));
            } else {
                vol_20[i] = NAN;
            }
        }

        std::vector<float> vol_slope(n);
        for (size_t i = 0; i < n; ++i) {
            if (i < static_cast<size_t>(w) || std::isnan(vol_20[i]) || std::isnan(vol_20[i - w]) || vol_20[i - w] < 1e-10) {
                vol_slope[i] = NAN;
            } else {
                vol_slope[i] = (vol_20[i] - vol_20[i - w]) / vol_20[i - w];
            }
        }

        #pragma omp critical
        {
            all_features_["vol_slope_" + std::to_string(w) + "b"] = vol_slope;
        }
        progress_.completed_features.fetch_add(1);
        progress_.update_progress();
    }

    // 9. Max drawdown: 3 windows = 3
    std::vector<int> max_dd_windows = {60, 144, 288};
    #pragma omp parallel for schedule(dynamic)
    for (size_t w_idx = 0; w_idx < max_dd_windows.size(); ++w_idx) {
        int w = max_dd_windows[w_idx];

        std::vector<float> close_lag(n);
        for (size_t i = 1; i < n; ++i) {
            close_lag[i] = close[i-1];
        }

        std::vector<float> max_val(n);
        for (size_t i = 0; i < n; ++i) {
            if (i + 1 < static_cast<size_t>(w)) {
                max_val[i] = NAN;
                continue;
            }
            float max_v = -std::numeric_limits<float>::infinity();
            for (int j = 0; j < w; ++j) {
                if (!std::isnan(close_lag[i - j])) {
                    max_v = std::max(max_v, close_lag[i - j]);
                }
            }
            max_val[i] = std::isfinite(max_v) ? max_v : NAN;
        }

        std::vector<float> max_dd(n);
        for (size_t i = 0; i < n; ++i) {
            if (!std::isnan(max_val[i]) && max_val[i] > 1e-10) {
                max_dd[i] = (close_lag[i] - max_val[i]) / max_val[i];
            } else {
                max_dd[i] = NAN;
            }
        }

        #pragma omp critical
        {
            all_features_["max_dd_" + std::to_string(w) + "b"] = max_dd;
        }
        progress_.completed_features.fetch_add(1);
        progress_.update_progress();
    }

    // 10. Return skew + kurtosis proxy: 10 windows × 2 = 20
    std::vector<int> skew_windows = {20, 30, 60, 90, 120, 144, 200, 288, 400, 576};
    #pragma omp parallel for schedule(dynamic)
    for (size_t w_idx = 0; w_idx < skew_windows.size(); ++w_idx) {
        int w = skew_windows[w_idx];

        std::vector<float> skew(n), kurt_proxy(n);
        for (size_t i = 0; i < n; ++i) {
            if (i + 1 < static_cast<size_t>(w)) {
                skew[i] = kurt_proxy[i] = NAN;
                continue;
            }

            // Compute mean/std/skew
            double sum = 0.0, sum_sq = 0.0, sum_cube = 0.0;
            int count = 0;
            for (int j = 0; j < w; ++j) {
                if (!std::isnan(log_ret[i - j])) {
                    sum += log_ret[i - j];
                    sum_sq += log_ret[i - j] * log_ret[i - j];
                    count++;
                }
            }

            if (count > 2) {
                double mean = sum / count;
                double var = (sum_sq / count) - mean * mean;
                double std_dev = std::sqrt(std::max(0.0, var));

                for (int j = 0; j < w; ++j) {
                    if (!std::isnan(log_ret[i - j])) {
                        double dev = log_ret[i - j] - mean;
                        sum_cube += dev * dev * dev;
                    }
                }

                if (std_dev > 1e-10) {
                    double skew_val = (sum_cube / count) / std::pow(std_dev, 3);
                    skew[i] = skew_val;
                    kurt_proxy[i] = std_dev / std::abs(mean > 1e-10 ? mean : 1e-10);
                } else {
                    skew[i] = kurt_proxy[i] = NAN;
                }
            } else {
                skew[i] = kurt_proxy[i] = NAN;
            }
        }

        #pragma omp critical
        {
            all_features_["ret_skew_" + std::to_string(w) + "b"] = skew;
            all_features_["ret_kurt_proxy_" + std::to_string(w) + "b"] = kurt_proxy;
        }
        progress_.completed_features.fetch_add(2);
        progress_.update_progress();
    }
}

// TREND/MOMENTUM (MASSIVE → ~500 features)
void DatasetBuilderV2::build_trend_features() {
    size_t n = raw_data_->num_rows;

    std::vector<float> close(n);
    for (size_t i = 1; i < n; ++i) {
        close[i] = raw_data_->close[i-1];  // Lag by 1
    }

    // 1. EMA gaps: 20 spans = 20
    std::vector<int> ema_spans = {5, 8, 10, 13, 15, 21, 26, 34, 42, 55, 68, 89, 110, 144, 180, 233, 288, 377, 465, 610};
    #pragma omp parallel for schedule(dynamic)
    for (size_t span_idx = 0; span_idx < ema_spans.size(); ++span_idx) {
        int span = ema_spans[span_idx];
        double alpha = 2.0 / (span + 1);

        std::vector<float> ema(n);
        double ema_val = 0.0;
        bool init = false;
        for (size_t i = 1; i < n; ++i) {
            if (!std::isnan(close[i])) {
                if (!init) {
                    ema_val = close[i];
                    init = true;
                } else {
                    ema_val = alpha * close[i] + (1 - alpha) * ema_val;
                }
                ema[i] = ema_val;
            } else {
                ema[i] = NAN;
            }
        }

        std::vector<float> ema_gap(n);
        for (size_t i = 0; i < n; ++i) {
            if (!std::isnan(ema[i]) && ema[i] > 1e-10) {
                ema_gap[i] = (close[i] - ema[i]) / ema[i];
            } else {
                ema_gap[i] = NAN;
            }
        }

        #pragma omp critical
        {
            all_features_["ema_gap_" + std::to_string(span) + "b"] = ema_gap;
        }
        progress_.completed_features.fetch_add(1);
        progress_.update_progress();
    }

    // 2. SMA gaps: 15 windows = 15
    std::vector<int> sma_windows = {5, 10, 15, 20, 30, 40, 50, 60, 80, 100, 120, 150, 200, 250, 300};
    #pragma omp parallel for schedule(dynamic)
    for (size_t w_idx = 0; w_idx < sma_windows.size(); ++w_idx) {
        int w = sma_windows[w_idx];

        std::vector<float> sma(n);
        for (size_t i = 0; i < n; ++i) {
            if (i + 1 < static_cast<size_t>(w)) {
                sma[i] = NAN;
                continue;
            }
            double sum = 0.0;
            int count = 0;
            for (int j = 0; j < w; ++j) {
                if (!std::isnan(close[i - j])) {
                    sum += close[i - j];
                    count++;
                }
            }
            sma[i] = count > 0 ? sum / count : NAN;
        }

        std::vector<float> sma_gap(n);
        for (size_t i = 0; i < n; ++i) {
            if (!std::isnan(sma[i]) && sma[i] > 1e-10) {
                sma_gap[i] = (close[i] - sma[i]) / sma[i];
            } else {
                sma_gap[i] = NAN;
            }
        }

        #pragma omp critical
        {
            all_features_["sma_gap_" + std::to_string(w) + "b"] = sma_gap;
        }
        progress_.completed_features.fetch_add(1);
        progress_.update_progress();
    }

    // 3. EMA ratios: 19 pairs = 19
    std::vector<std::pair<int, int>> ema_pairs = {
        {5, 20}, {5, 60}, {8, 21}, {8, 34}, {10, 30}, {10, 60}, {13, 34},
        {13, 55}, {21, 55}, {21, 89}, {21, 144}, {34, 89}, {34, 144},
        {55, 144}, {55, 233}, {89, 233}, {89, 377}, {144, 288}, {144, 377}
    };
    #pragma omp parallel for schedule(dynamic)
    for (size_t pair_idx = 0; pair_idx < ema_pairs.size(); ++pair_idx) {
        int fast = ema_pairs[pair_idx].first;
        int slow = ema_pairs[pair_idx].second;
        double alpha_f = 2.0 / (fast + 1);
        double alpha_s = 2.0 / (slow + 1);

        std::vector<float> ema_f(n), ema_s(n);
        double ema_f_val = 0.0, ema_s_val = 0.0;
        bool init_f = false, init_s = false;

        for (size_t i = 1; i < n; ++i) {
            if (!std::isnan(close[i])) {
                if (!init_f) {
                    ema_f_val = close[i];
                    init_f = true;
                } else {
                    ema_f_val = alpha_f * close[i] + (1 - alpha_f) * ema_f_val;
                }
                ema_f[i] = ema_f_val;

                if (!init_s) {
                    ema_s_val = close[i];
                    init_s = true;
                } else {
                    ema_s_val = alpha_s * close[i] + (1 - alpha_s) * ema_s_val;
                }
                ema_s[i] = ema_s_val;
            } else {
                ema_f[i] = ema_s[i] = NAN;
            }
        }

        std::vector<float> ema_ratio(n);
        for (size_t i = 0; i < n; ++i) {
            if (!std::isnan(ema_s[i]) && ema_s[i] > 1e-10) {
                ema_ratio[i] = ema_f[i] / ema_s[i] - 1.0f;
            } else {
                ema_ratio[i] = NAN;
            }
        }

        #pragma omp critical
        {
            all_features_["ema_ratio_" + std::to_string(fast) + "_" + std::to_string(slow) + "b"] = ema_ratio;
        }
        progress_.completed_features.fetch_add(1);
        progress_.update_progress();
    }

    // 4. Slope: 15 windows = 15
    std::vector<int> slope_windows = {3, 5, 8, 10, 15, 20, 30, 40, 50, 60, 90, 120, 144, 200, 288};
    #pragma omp parallel for schedule(dynamic)
    for (size_t w_idx = 0; w_idx < slope_windows.size(); ++w_idx) {
        int w = slope_windows[w_idx];

        std::vector<float> slope(n);
        for (size_t i = 0; i < n; ++i) {
            if (i < static_cast<size_t>(w) || std::isnan(close[i]) || std::isnan(close[i - w]) || close[i - w] < 1e-10) {
                slope[i] = NAN;
            } else {
                slope[i] = (close[i] - close[i - w]) / (w * close[i - w]);
            }
        }

        #pragma omp critical
        {
            all_features_["slope_" + std::to_string(w) + "b"] = slope;
        }
        progress_.completed_features.fetch_add(1);
        progress_.update_progress();
    }

    // 5. Momentum (ROC): 20 horizons = 20
    std::vector<int> mom_horizons = {3, 5, 8, 10, 13, 20, 21, 30, 34, 40, 55, 60, 89, 100, 120, 144, 200, 233, 288, 377};
    #pragma omp parallel for schedule(dynamic)
    for (size_t h_idx = 0; h_idx < mom_horizons.size(); ++h_idx) {
        int h = mom_horizons[h_idx];

        std::vector<float> mom(n);
        for (size_t i = 0; i < n; ++i) {
            if (i < static_cast<size_t>(h) || std::isnan(close[i]) || std::isnan(close[i - h]) || close[i - h] < 1e-10) {
                mom[i] = NAN;
            } else {
                mom[i] = (close[i] - close[i - h]) / close[i - h];
            }
        }

        #pragma omp critical
        {
            all_features_["mom_" + std::to_string(h) + "b"] = mom;
        }
        progress_.completed_features.fetch_add(1);
        progress_.update_progress();
    }

    // 6. RSI: 13 windows × 2 (RSI + Stochastic RSI) = 26
    std::vector<float> log_ret(n);
    for (size_t i = 2; i < n; ++i) {
        if (!std::isnan(close[i]) && !std::isnan(close[i-1]) && close[i-1] > 1e-10) {
            log_ret[i] = std::log(close[i] / close[i-1]);
        } else {
            log_ret[i] = NAN;
        }
    }

    std::vector<int> rsi_windows = {5, 7, 10, 14, 20, 21, 28, 34, 42, 55, 70, 84, 100};
    #pragma omp parallel for schedule(dynamic)
    for (size_t w_idx = 0; w_idx < rsi_windows.size(); ++w_idx) {
        int w = rsi_windows[w_idx];

        std::vector<float> gain(n), loss(n);
        for (size_t i = 0; i < n; ++i) {
            if (!std::isnan(log_ret[i])) {
                gain[i] = log_ret[i] > 0 ? log_ret[i] : 0.0f;
                loss[i] = log_ret[i] < 0 ? -log_ret[i] : 0.0f;
            } else {
                gain[i] = loss[i] = NAN;
            }
        }

        std::vector<float> rsi(n), stoch_rsi(n);
        for (size_t i = 0; i < n; ++i) {
            if (i + 1 < static_cast<size_t>(w)) {
                rsi[i] = stoch_rsi[i] = NAN;
                continue;
            }

            double sum_gain = 0.0, sum_loss = 0.0;
            int count = 0;
            for (int j = 0; j < w; ++j) {
                if (!std::isnan(gain[i - j])) {
                    sum_gain += gain[i - j];
                    sum_loss += loss[i - j];
                    count++;
                }
            }

            if (count > 0) {
                double avg_gain = sum_gain / count;
                double avg_loss = sum_loss / count;
                double rs = avg_loss > 1e-10 ? avg_gain / avg_loss : 100.0;
                rsi[i] = 100.0 - (100.0 / (1.0 + rs));
            } else {
                rsi[i] = NAN;
            }
        }

        // Stochastic RSI
        for (size_t i = 0; i < n; ++i) {
            if (i + 1 < static_cast<size_t>(w)) {
                stoch_rsi[i] = NAN;
                continue;
            }

            float rsi_min = std::numeric_limits<float>::infinity();
            float rsi_max = -std::numeric_limits<float>::infinity();
            for (int j = 0; j < w; ++j) {
                if (!std::isnan(rsi[i - j])) {
                    rsi_min = std::min(rsi_min, rsi[i - j]);
                    rsi_max = std::max(rsi_max, rsi[i - j]);
                }
            }

            if (std::isfinite(rsi_min) && std::isfinite(rsi_max) && rsi_max - rsi_min > 1e-10) {
                stoch_rsi[i] = (rsi[i] - rsi_min) / (rsi_max - rsi_min) * 100.0;
            } else {
                stoch_rsi[i] = NAN;
            }
        }

        #pragma omp critical
        {
            all_features_["rsi_" + std::to_string(w) + "b"] = rsi;
            all_features_["stoch_rsi_" + std::to_string(w) + "b"] = stoch_rsi;
        }
        progress_.completed_features.fetch_add(2);
        progress_.update_progress();
    }

    // 7. Stochastic K/D: 4 windows × 2 = 8
    std::vector<float> high_lag(n), low_lag(n);
    for (size_t i = 1; i < n; ++i) {
        high_lag[i] = raw_data_->high[i-1];
        low_lag[i] = raw_data_->low[i-1];
    }

    std::vector<int> stoch_windows = {5, 14, 21, 55};
    #pragma omp parallel for schedule(dynamic)
    for (size_t w_idx = 0; w_idx < stoch_windows.size(); ++w_idx) {
        int w = stoch_windows[w_idx];

        std::vector<float> stoch_k(n), stoch_d(n);
        for (size_t i = 0; i < n; ++i) {
            if (i + 1 < static_cast<size_t>(w)) {
                stoch_k[i] = NAN;
                continue;
            }

            float hh = -std::numeric_limits<float>::infinity();
            float ll = std::numeric_limits<float>::infinity();
            for (int j = 0; j < w; ++j) {
                if (!std::isnan(high_lag[i - j])) {
                    hh = std::max(hh, high_lag[i - j]);
                }
                if (!std::isnan(low_lag[i - j])) {
                    ll = std::min(ll, low_lag[i - j]);
                }
            }

            if (std::isfinite(hh) && std::isfinite(ll) && hh - ll > 1e-10) {
                stoch_k[i] = (close[i] - ll) / (hh - ll) * 100.0;
            } else {
                stoch_k[i] = NAN;
            }
        }

        // %D = 3-period SMA of %K
        for (size_t i = 0; i < n; ++i) {
            if (i + 1 < 3) {
                stoch_d[i] = NAN;
                continue;
            }

            double sum = 0.0;
            int count = 0;
            for (int j = 0; j < 3; ++j) {
                if (!std::isnan(stoch_k[i - j])) {
                    sum += stoch_k[i - j];
                    count++;
                }
            }
            stoch_d[i] = count > 0 ? sum / count : NAN;
        }

        #pragma omp critical
        {
            all_features_["stoch_k_" + std::to_string(w) + "b"] = stoch_k;
            all_features_["stoch_d_" + std::to_string(w) + "b"] = stoch_d;
        }
        progress_.completed_features.fetch_add(2);
        progress_.update_progress();
    }

    // 8. MACD: 4 configs × 2 = 8
    std::vector<std::tuple<int, int, int>> macd_configs = {{12, 26, 9}, {5, 34, 5}, {8, 21, 5}, {21, 55, 13}};
    #pragma omp parallel for schedule(dynamic)
    for (size_t cfg_idx = 0; cfg_idx < macd_configs.size(); ++cfg_idx) {
        auto [fast, slow, sig] = macd_configs[cfg_idx];

        double alpha_f = 2.0 / (fast + 1);
        double alpha_s = 2.0 / (slow + 1);
        double alpha_sig = 2.0 / (sig + 1);

        std::vector<float> ema_f(n), ema_s(n);
        double ema_f_val = 0.0, ema_s_val = 0.0;
        bool init_f = false, init_s = false;

        for (size_t i = 1; i < n; ++i) {
            if (!std::isnan(close[i])) {
                if (!init_f) {
                    ema_f_val = close[i];
                    init_f = true;
                } else {
                    ema_f_val = alpha_f * close[i] + (1 - alpha_f) * ema_f_val;
                }
                ema_f[i] = ema_f_val;

                if (!init_s) {
                    ema_s_val = close[i];
                    init_s = true;
                } else {
                    ema_s_val = alpha_s * close[i] + (1 - alpha_s) * ema_s_val;
                }
                ema_s[i] = ema_s_val;
            } else {
                ema_f[i] = ema_s[i] = NAN;
            }
        }

        std::vector<float> macd_line(n), signal_line(n), macd_hist(n);
        double signal_val = 0.0;
        bool init_sig = false;

        for (size_t i = 0; i < n; ++i) {
            if (!std::isnan(ema_f[i]) && !std::isnan(ema_s[i])) {
                macd_line[i] = (ema_f[i] - ema_s[i]) / (close[i] > 1e-10 ? close[i] : 1.0);

                if (!init_sig) {
                    signal_val = macd_line[i];
                    init_sig = true;
                } else {
                    signal_val = alpha_sig * macd_line[i] + (1 - alpha_sig) * signal_val;
                }
                signal_line[i] = signal_val;
                macd_hist[i] = macd_line[i] - signal_line[i];
            } else {
                macd_line[i] = signal_line[i] = macd_hist[i] = NAN;
            }
        }

        #pragma omp critical
        {
            std::string suffix = std::to_string(fast) + "_" + std::to_string(slow) + "_" + std::to_string(sig);
            all_features_["macd_" + suffix] = macd_line;
            all_features_["macd_hist_" + suffix] = macd_hist;
        }
        progress_.completed_features.fetch_add(2);
        progress_.update_progress();
    }

    // 9. Bollinger Bands: 10 windows × 3 = 30
    std::vector<int> bb_windows = {10, 15, 20, 26, 34, 42, 55, 70, 89, 120};
    #pragma omp parallel for schedule(dynamic)
    for (size_t w_idx = 0; w_idx < bb_windows.size(); ++w_idx) {
        int w = bb_windows[w_idx];

        std::vector<float> sma(n), std_dev(n);
        for (size_t i = 0; i < n; ++i) {
            if (i + 1 < static_cast<size_t>(w)) {
                sma[i] = std_dev[i] = NAN;
                continue;
            }

            double sum = 0.0, sum_sq = 0.0;
            int count = 0;
            for (int j = 0; j < w; ++j) {
                if (!std::isnan(close[i - j])) {
                    sum += close[i - j];
                    sum_sq += close[i - j] * close[i - j];
                    count++;
                }
            }

            if (count > 1) {
                sma[i] = sum / count;
                double var = (sum_sq / count) - (sma[i] * sma[i]);
                std_dev[i] = std::sqrt(std::max(0.0, var));
            } else {
                sma[i] = std_dev[i] = NAN;
            }
        }

        std::vector<float> bb_pos(n), bb_width(n), bb_pct_b(n);
        for (size_t i = 0; i < n; ++i) {
            if (!std::isnan(sma[i]) && std_dev[i] > 1e-10) {
                bb_pos[i] = (close[i] - sma[i]) / (2 * std_dev[i]);
                bb_width[i] = (2 * std_dev[i]) / (sma[i] > 1e-10 ? sma[i] : 1.0);
                bb_pct_b[i] = (close[i] - (sma[i] - 2 * std_dev[i])) / (4 * std_dev[i]);
            } else {
                bb_pos[i] = bb_width[i] = bb_pct_b[i] = NAN;
            }
        }

        #pragma omp critical
        {
            all_features_["bb_pos_" + std::to_string(w) + "b"] = bb_pos;
            all_features_["bb_width_" + std::to_string(w) + "b"] = bb_width;
            all_features_["bb_pct_b_" + std::to_string(w) + "b"] = bb_pct_b;
        }
        progress_.completed_features.fetch_add(3);
        progress_.update_progress();
    }

    // Done
}

// SESSION/CALENDAR (~50 features)
void DatasetBuilderV2::build_session_features() {
    size_t n = raw_data_->num_rows;
    const auto& timestamps = raw_data_->timestamps;

    // Basic time features
    std::vector<float> hour(n), minute_bucket(n), dow(n), dom(n), month(n);
    std::vector<float> sin_hour(n), cos_hour(n), sin_dow(n), cos_dow(n), sin_month(n), cos_month(n);
    std::vector<float> is_asia(n), is_london(n), is_ny(n);

    #pragma omp parallel for
    for (size_t i = 0; i < n; ++i) {
        // Convert timestamp (microseconds) to hour/minute/day
        int64_t ts = timestamps[i];
        int64_t seconds_in_day = (ts / 1000000) % 86400;
        int h = seconds_in_day / 3600;
        int m = (seconds_in_day % 3600) / 60;

        // Date extraction (simplified - assumes UTC)
        int64_t days_since_epoch = ts / (1000000LL * 86400);
        int d_of_week = (days_since_epoch + 4) % 7;  // Epoch was Thursday
        int d_of_month = (days_since_epoch % 30) + 1;  // Rough approximation
        int mon = ((days_since_epoch / 30) % 12) + 1;

        hour[i] = h;
        minute_bucket[i] = m / 5;
        dow[i] = d_of_week;
        dom[i] = d_of_month;
        month[i] = mon;

        // Cyclical
        sin_hour[i] = std::sin(h * 2 * M_PI / 24.0);
        cos_hour[i] = std::cos(h * 2 * M_PI / 24.0);
        sin_dow[i] = std::sin(d_of_week * 2 * M_PI / 7.0);
        cos_dow[i] = std::cos(d_of_week * 2 * M_PI / 7.0);
        sin_month[i] = std::sin(mon * 2 * M_PI / 12.0);
        cos_month[i] = std::cos(mon * 2 * M_PI / 12.0);

        // Sessions
        is_asia[i] = (h >= 0 && h < 8) ? 1.0f : 0.0f;
        is_london[i] = (h >= 7 && h < 16) ? 1.0f : 0.0f;
        is_ny[i] = (h >= 12 && h < 21) ? 1.0f : 0.0f;
    }

    #pragma omp critical
    {
        all_features_["hour"] = hour;
        all_features_["minute_bucket"] = minute_bucket;
        all_features_["dow"] = dow;
        all_features_["dom"] = dom;
        all_features_["month"] = month;
        all_features_["sin_hour"] = sin_hour;
        all_features_["cos_hour"] = cos_hour;
        all_features_["sin_dow"] = sin_dow;
        all_features_["cos_dow"] = cos_dow;
        all_features_["sin_month"] = sin_month;
        all_features_["cos_month"] = cos_month;
        all_features_["is_asia"] = is_asia;
        all_features_["is_london"] = is_london;
        all_features_["is_ny"] = is_ny;
    }

    progress_.completed_features.fetch_add(14);
    progress_.update_progress();

    // Session return/vol stats: 3 sessions × 3 stats × 2 = 18
    std::vector<std::string> sessions = {"asia", "london", "ny"};
    std::vector<int> session_hours_start = {0, 7, 12};
    std::vector<int> session_hours_end = {8, 16, 21};

    const auto& close_raw = raw_data_->close;
    std::vector<float> log_ret_1(n);
    for (size_t i = 2; i < n; ++i) {
        if (!std::isnan(close_raw[i-1]) && !std::isnan(close_raw[i-2]) && close_raw[i-2] > 1e-10) {
            log_ret_1[i] = std::log(close_raw[i-1] / close_raw[i-2]);
        } else {
            log_ret_1[i] = NAN;
        }
    }

    #pragma omp parallel for schedule(dynamic)
    for (size_t s_idx = 0; s_idx < sessions.size(); ++s_idx) {
        int h_start = session_hours_start[s_idx];
        int h_end = session_hours_end[s_idx];

        // Rolling 20-bar session return/vol
        std::vector<float> sess_ret(n), sess_vol(n), sess_ret_20(n);
        for (size_t i = 0; i < n; ++i) {
            int64_t ts = timestamps[i];
            int64_t seconds_in_day = (ts / 1000000) % 86400;
            int h = seconds_in_day / 3600;

            bool in_session = (h >= h_start && h < h_end);
            sess_ret[i] = in_session ? log_ret_1[i] : 0.0f;
        }

        // Cumulative session return (20-bar)
        for (size_t i = 0; i < n; ++i) {
            if (i + 1 < 20) {
                sess_ret_20[i] = NAN;
                continue;
            }
            double sum = 0.0;
            for (int j = 0; j < 20; ++j) {
                sum += sess_ret[i - j];
            }
            sess_ret_20[i] = sum;
        }

        // Session vol (20-bar)
        for (size_t i = 0; i < n; ++i) {
            if (i + 1 < 20) {
                sess_vol[i] = NAN;
                continue;
            }
            double sum = 0.0, sum_sq = 0.0;
            int count = 0;
            for (int j = 0; j < 20; ++j) {
                if (sess_ret[i - j] != 0.0f && !std::isnan(sess_ret[i - j])) {
                    sum += sess_ret[i - j];
                    sum_sq += sess_ret[i - j] * sess_ret[i - j];
                    count++;
                }
            }
            if (count > 1) {
                double mean = sum / count;
                double var = (sum_sq / count) - mean * mean;
                sess_vol[i] = std::sqrt(std::max(0.0, var));
            } else {
                sess_vol[i] = NAN;
            }
        }

        #pragma omp critical
        {
            all_features_[sessions[s_idx] + "_ret_20b"] = sess_ret_20;
            all_features_[sessions[s_idx] + "_vol_20b"] = sess_vol;
        }
        progress_.completed_features.fetch_add(2);
        progress_.update_progress();
    }

    // Day-of-week effects: 7 days × 2 = 14
    for (int d = 0; d < 7; ++d) {
        std::vector<float> dow_ret(n), dow_vol(n);
        for (size_t i = 0; i < n; ++i) {
            int64_t ts = timestamps[i];
            int64_t days_since_epoch = ts / (1000000LL * 86400);
            int d_of_week = (days_since_epoch + 4) % 7;

            dow_ret[i] = (d_of_week == d) ? log_ret_1[i] : 0.0f;
        }

        // Rolling 60-bar DOW return
        for (size_t i = 0; i < n; ++i) {
            if (i + 1 < 60) {
                dow_vol[i] = NAN;
                continue;
            }
            double sum = 0.0, sum_sq = 0.0;
            int count = 0;
            for (int j = 0; j < 60; ++j) {
                if (dow_ret[i - j] != 0.0f && !std::isnan(dow_ret[i - j])) {
                    sum += dow_ret[i - j];
                    sum_sq += dow_ret[i - j] * dow_ret[i - j];
                    count++;
                }
            }
            if (count > 1) {
                double mean = sum / count;
                double var = (sum_sq / count) - mean * mean;
                dow_vol[i] = std::sqrt(std::max(0.0, var));
            } else {
                dow_vol[i] = NAN;
            }
        }

        all_features_["dow_" + std::to_string(d) + "_vol_60b"] = dow_vol;
    }
    progress_.completed_features.fetch_add(7);
    progress_.update_progress();

    // Time-to-event features: 6
    std::vector<float> bars_since_asia_open(n), bars_since_london_open(n), bars_since_ny_open(n);
    std::vector<float> bars_until_asia_close(n), bars_until_london_close(n), bars_until_ny_close(n);

    for (size_t i = 0; i < n; ++i) {
        int64_t ts = timestamps[i];
        int64_t seconds_in_day = (ts / 1000000) % 86400;
        int h = seconds_in_day / 3600;

        bars_since_asia_open[i] = h >= 0 ? h : NAN;
        bars_since_london_open[i] = h >= 7 ? h - 7 : NAN;
        bars_since_ny_open[i] = h >= 12 ? h - 12 : NAN;

        bars_until_asia_close[i] = h < 8 ? 8 - h : NAN;
        bars_until_london_close[i] = h < 16 ? 16 - h : NAN;
        bars_until_ny_close[i] = h < 21 ? 21 - h : NAN;
    }

    all_features_["bars_since_asia_open"] = bars_since_asia_open;
    all_features_["bars_since_london_open"] = bars_since_london_open;
    all_features_["bars_since_ny_open"] = bars_since_ny_open;
    all_features_["bars_until_asia_close"] = bars_until_asia_close;
    all_features_["bars_until_london_close"] = bars_until_london_close;
    all_features_["bars_until_ny_close"] = bars_until_ny_close;

    progress_.completed_features.fetch_add(6);
    progress_.update_progress();
}

// MICROSTRUCTURE (~60 features)
void DatasetBuilderV2::build_micro_features() {
    size_t n = raw_data_->num_rows;
    const auto& spread = raw_data_->spread;
    const auto& tick_volume = raw_data_->tick_volume;

    std::vector<int> windows = {5, 20, 60, 144, 288};

    // Spread mean/std/min/max: 5 windows × 4 = 20
    #pragma omp parallel for schedule(dynamic)
    for (size_t w_idx = 0; w_idx < windows.size(); ++w_idx) {
        int w = windows[w_idx];

        std::vector<float> spread_mean(n), spread_std(n), spread_min(n), spread_max(n);
        rolling_mean_std(spread, w, spread_mean, spread_std);

        for (size_t i = 0; i < n; ++i) {
            if (i + 1 < static_cast<size_t>(w)) {
                spread_min[i] = spread_max[i] = NAN;
                continue;
            }

            float min_v = std::numeric_limits<float>::infinity();
            float max_v = -std::numeric_limits<float>::infinity();
            for (int j = 0; j < w; ++j) {
                if (!std::isnan(spread[i - j])) {
                    min_v = std::min(min_v, spread[i - j]);
                    max_v = std::max(max_v, spread[i - j]);
                }
            }
            spread_min[i] = std::isfinite(min_v) ? min_v : NAN;
            spread_max[i] = std::isfinite(max_v) ? max_v : NAN;
        }

        #pragma omp critical
        {
            all_features_["spread_mean_" + std::to_string(w) + "b"] = spread_mean;
            all_features_["spread_std_" + std::to_string(w) + "b"] = spread_std;
            all_features_["spread_min_" + std::to_string(w) + "b"] = spread_min;
            all_features_["spread_max_" + std::to_string(w) + "b"] = spread_max;
        }
        progress_.completed_features.fetch_add(4);
        progress_.update_progress();
    }

    // Tick volume mean/std/sum: 5 windows × 3 = 15
    #pragma omp parallel for schedule(dynamic)
    for (size_t w_idx = 0; w_idx < windows.size(); ++w_idx) {
        int w = windows[w_idx];

        std::vector<float> tvol_mean(n), tvol_std(n), tvol_sum(n);
        rolling_mean_std(tick_volume, w, tvol_mean, tvol_std);

        for (size_t i = 0; i < n; ++i) {
            if (i + 1 < static_cast<size_t>(w)) {
                tvol_sum[i] = NAN;
                continue;
            }

            double sum = 0.0;
            for (int j = 0; j < w; ++j) {
                if (!std::isnan(tick_volume[i - j])) {
                    sum += tick_volume[i - j];
                }
            }
            tvol_sum[i] = sum;
        }

        #pragma omp critical
        {
            all_features_["tvol_mean_" + std::to_string(w) + "b"] = tvol_mean;
            all_features_["tvol_std_" + std::to_string(w) + "b"] = tvol_std;
            all_features_["tvol_sum_" + std::to_string(w) + "b"] = tvol_sum;
        }
        progress_.completed_features.fetch_add(3);
        progress_.update_progress();
    }

    // Spread-to-volatility ratio: 5 windows = 5
    const auto& close_raw = raw_data_->close;
    std::vector<float> log_ret(n);
    for (size_t i = 2; i < n; ++i) {
        if (!std::isnan(close_raw[i-1]) && !std::isnan(close_raw[i-2]) && close_raw[i-2] > 1e-10) {
            log_ret[i] = std::log(close_raw[i-1] / close_raw[i-2]);
        } else {
            log_ret[i] = NAN;
        }
    }

    #pragma omp parallel for schedule(dynamic)
    for (size_t w_idx = 0; w_idx < windows.size(); ++w_idx) {
        int w = windows[w_idx];

        std::vector<float> vol(n);
        for (size_t i = 0; i < n; ++i) {
            if (i + 1 < static_cast<size_t>(w)) {
                vol[i] = NAN;
                continue;
            }

            double sum = 0.0, sum_sq = 0.0;
            int count = 0;
            for (int j = 0; j < w; ++j) {
                if (!std::isnan(log_ret[i - j])) {
                    sum += log_ret[i - j];
                    sum_sq += log_ret[i - j] * log_ret[i - j];
                    count++;
                }
            }

            if (count > 1) {
                double mean = sum / count;
                double var = (sum_sq / count) - mean * mean;
                vol[i] = std::sqrt(std::max(0.0, var));
            } else {
                vol[i] = NAN;
            }
        }

        std::vector<float> spread_mean(n), dummy(n);
        rolling_mean_std(spread, w, spread_mean, dummy);

        std::vector<float> spread_vol_ratio(n);
        for (size_t i = 0; i < n; ++i) {
            if (!std::isnan(spread_mean[i]) && vol[i] > 1e-10) {
                spread_vol_ratio[i] = spread_mean[i] / vol[i];
            } else {
                spread_vol_ratio[i] = NAN;
            }
        }

        #pragma omp critical
        {
            all_features_["spread_vol_ratio_" + std::to_string(w) + "b"] = spread_vol_ratio;
        }
        progress_.completed_features.fetch_add(1);
        progress_.update_progress();
    }

    // Tick volume per pip: 5 windows = 5
    #pragma omp parallel for schedule(dynamic)
    for (size_t w_idx = 0; w_idx < windows.size(); ++w_idx) {
        int w = windows[w_idx];

        std::vector<float> tvol_per_pip(n);
        for (size_t i = 0; i < n; ++i) {
            if (i + 1 < static_cast<size_t>(w)) {
                tvol_per_pip[i] = NAN;
                continue;
            }

            double sum_tvol = 0.0, sum_range = 0.0;
            for (int j = 0; j < w; ++j) {
                if (!std::isnan(tick_volume[i - j])) {
                    sum_tvol += tick_volume[i - j];
                }
                if (!std::isnan(raw_data_->high[i - j]) && !std::isnan(raw_data_->low[i - j])) {
                    sum_range += raw_data_->high[i - j] - raw_data_->low[i - j];
                }
            }

            if (sum_range > 1e-10) {
                tvol_per_pip[i] = sum_tvol / sum_range;
            } else {
                tvol_per_pip[i] = NAN;
            }
        }

        #pragma omp critical
        {
            all_features_["tvol_per_pip_" + std::to_string(w) + "b"] = tvol_per_pip;
        }
        progress_.completed_features.fetch_add(1);
        progress_.update_progress();
    }

    // Effective spread (bid-ask bounce proxy): 4 windows = 4
    std::vector<int> bounce_windows = {5, 20, 60, 144};
    #pragma omp parallel for schedule(dynamic)
    for (size_t w_idx = 0; w_idx < bounce_windows.size(); ++w_idx) {
        int w = bounce_windows[w_idx];

        std::vector<float> eff_spread(n);
        for (size_t i = 0; i < n; ++i) {
            if (i + 1 < static_cast<size_t>(w)) {
                eff_spread[i] = NAN;
                continue;
            }

            double sum_abs_ret = 0.0;
            int count = 0;
            for (int j = 1; j < w; ++j) {
                if (!std::isnan(close_raw[i - j + 1]) && !std::isnan(close_raw[i - j]) && close_raw[i - j] > 1e-10) {
                    double ret = (close_raw[i - j + 1] - close_raw[i - j]) / close_raw[i - j];
                    sum_abs_ret += std::abs(ret);
                    count++;
                }
            }

            eff_spread[i] = count > 0 ? sum_abs_ret / count : NAN;
        }

        #pragma omp critical
        {
            all_features_["eff_spread_" + std::to_string(w) + "b"] = eff_spread;
        }
        progress_.completed_features.fetch_add(1);
        progress_.update_progress();
    }
}

// Merge features
bool DatasetBuilderV2::merge_features() {
    log("Merging " + std::to_string(all_features_.size()) + " feature columns");

    size_t n = raw_data_->num_rows;

    // Build Arrow schema
    std::vector<std::shared_ptr<arrow::Field>> fields;
    fields.push_back(arrow::field("time", arrow::timestamp(arrow::TimeUnit::MICRO)));

    // OHLCV
    for (auto col : {"open", "high", "low", "close", "tick_volume", "spread"}) {
        fields.push_back(arrow::field(col, arrow::float32()));
    }

    // All features
    for (const auto& kv : all_features_) {
        fields.push_back(arrow::field(kv.first, arrow::float32()));
    }

    auto schema = arrow::schema(fields);

    // Build arrays
    std::vector<std::shared_ptr<arrow::Array>> arrays;

    // Time
    arrow::TimestampBuilder time_builder(arrow::timestamp(arrow::TimeUnit::MICRO), arrow::default_memory_pool());
    PARQUET_THROW_NOT_OK(time_builder.AppendValues(raw_data_->timestamps.data(), raw_data_->timestamps.size()));
    std::shared_ptr<arrow::Array> time_array;
    PARQUET_THROW_NOT_OK(time_builder.Finish(&time_array));
    arrays.push_back(time_array);

    // OHLCV
    for (auto vec : {&raw_data_->open, &raw_data_->high, &raw_data_->low, &raw_data_->close, &raw_data_->tick_volume, &raw_data_->spread}) {
        arrow::FloatBuilder builder(arrow::default_memory_pool());
        for (size_t i = 0; i < n; ++i) {
            if (std::isnan((*vec)[i])) {
                PARQUET_THROW_NOT_OK(builder.AppendNull());
            } else {
                PARQUET_THROW_NOT_OK(builder.Append((*vec)[i]));
            }
        }
        std::shared_ptr<arrow::Array> arr;
        PARQUET_THROW_NOT_OK(builder.Finish(&arr));
        arrays.push_back(arr);
    }

    // Features
    for (const auto& kv : all_features_) {
        arrow::FloatBuilder builder(arrow::default_memory_pool());
        for (size_t i = 0; i < n; ++i) {
            if (std::isnan(kv.second[i])) {
                PARQUET_THROW_NOT_OK(builder.AppendNull());
            } else {
                PARQUET_THROW_NOT_OK(builder.Append(kv.second[i]));
            }
        }
        std::shared_ptr<arrow::Array> arr;
        PARQUET_THROW_NOT_OK(builder.Finish(&arr));
        arrays.push_back(arr);
    }

    // Build table
    result_table_ = arrow::Table::Make(schema, arrays);
    return true;
}

// Add targets
bool DatasetBuilderV2::add_targets() {
    size_t n = raw_data_->num_rows;
    const auto& close = raw_data_->close;

    // Forward returns: 5, 10, 20, 72, 144, 288 bars
    std::vector<int> horizons = {5, 10, 20, 72, 144, 288};

    for (int h : horizons) {
        std::vector<float> fwd_ret(n);
        for (size_t i = 0; i < n; ++i) {
            if (i + h < n && !std::isnan(close[i]) && !std::isnan(close[i + h]) && close[i] > 1e-10) {
                fwd_ret[i] = (close[i + h] - close[i]) / close[i];
            } else {
                fwd_ret[i] = NAN;
            }
        }
        all_features_["fwd_ret_" + std::to_string(h) + "b"] = fwd_ret;

        // Labels (ternary: -1, 0, 1)
        std::vector<float> label(n);
        for (size_t i = 0; i < n; ++i) {
            if (std::isnan(fwd_ret[i])) {
                label[i] = NAN;
            } else if (fwd_ret[i] > 0.0001) {
                label[i] = 1.0f;
            } else if (fwd_ret[i] < -0.0001) {
                label[i] = -1.0f;
            } else {
                label[i] = 0.0f;
            }
        }
        all_features_["label_" + std::to_string(h) + "b"] = label;
    }

    return true;
}

// Validate
bool DatasetBuilderV2::validate() {
    size_t n = raw_data_->num_rows;

    // Check for NaN counts
    size_t total_nan = 0;
    size_t total_cells = 0;

    for (const auto& kv : all_features_) {
        size_t nan_count = 0;
        for (size_t i = 0; i < n && i < kv.second.size(); ++i) {
            if (std::isnan(kv.second[i])) {
                nan_count++;
            }
        }
        total_nan += nan_count;
        total_cells += kv.second.size();
    }

    double nan_pct = 100.0 * total_nan / total_cells;
    log("NaN percentage: " + std::to_string(nan_pct) + "%");

    if (nan_pct > 50.0) {
        log("WARNING: High NaN percentage");
    }

    return true;
}

// Save output
bool DatasetBuilderV2::save_output() {
    log("Writing parquet to " + config_.output_path);

    if (!result_table_) {
        log("ERROR: result_table_ is null");
        return false;
    }

    log("Table has " + std::to_string(result_table_->num_rows()) + " rows, " + std::to_string(result_table_->num_columns()) + " cols");

    try {
        auto open_result = arrow::io::FileOutputStream::Open(config_.output_path);
        if (!open_result.ok()) {
            log("ERROR opening output file: " + open_result.status().ToString());
            return false;
        }
        std::shared_ptr<arrow::io::FileOutputStream> outfile = std::move(open_result).ValueOrDie();

        auto write_result = parquet::arrow::WriteTable(*result_table_, arrow::default_memory_pool(), outfile, 1000000);
        if (!write_result.ok()) {
            log("ERROR writing table: " + write_result.ToString());
            return false;
        }

        auto close_result = outfile->Close();
        if (!close_result.ok()) {
            log("ERROR closing file: " + close_result.ToString());
            return false;
        }

        log("Parquet written successfully");
        return true;
    } catch (const std::exception& e) {
        log("ERROR writing parquet: " + std::string(e.what()));
        return false;
    }
}

} // namespace dominion
