#include "dominion/pipeline.hpp"
#include "dominion/storage.hpp"
#include "dominion/sources.hpp"
#include "dominion/fusion.hpp"
#include "dominion/features.hpp"
#include "dominion/health.hpp"
#include "dominion/bus.hpp"

#include <chrono>
#include <iostream>
#include <random>
#include <sstream>
#include <iomanip>

namespace dominion {

namespace {
    std::string generate_uuid() {
        // Simple UUID v4 generation without libuuid
        std::random_device rd;
        std::mt19937_64 gen(rd());
        std::uniform_int_distribution<uint64_t> dis;

        std::ostringstream oss;
        oss << std::hex << std::setfill('0');
        oss << std::setw(8) << (dis(gen) & 0xFFFFFFFF) << "-";
        oss << std::setw(4) << (dis(gen) & 0xFFFF) << "-";
        oss << std::setw(4) << ((dis(gen) & 0x0FFF) | 0x4000) << "-";  // Version 4
        oss << std::setw(4) << ((dis(gen) & 0x3FFF) | 0x8000) << "-";  // Variant
        oss << std::setw(12) << (dis(gen) & 0xFFFFFFFFFFFF);

        return oss.str();
    }

    std::string phase_name(PipelinePhase phase) {
        switch (phase) {
            case PipelinePhase::Init: return "Init";
            case PipelinePhase::FetchSources: return "FetchSources";
            case PipelinePhase::StoreRaw: return "StoreRaw";
            case PipelinePhase::FusePrices: return "FusePrices";
            case PipelinePhase::ReconstructTicks: return "ReconstructTicks";
            case PipelinePhase::ComputeFeatures: return "ComputeFeatures";
            case PipelinePhase::HealthChecks: return "HealthChecks";
            case PipelinePhase::Report: return "Report";
            case PipelinePhase::Complete: return "Complete";
        }
        return "Unknown";
    }
}

Pipeline::Pipeline(Config config)
    : config_(std::move(config)),
      storage_(std::make_unique<Storage>(config_.duckdb_path.string())),
      bus_(std::make_unique<BusPublisher>(config_.bus_url)) {}

Pipeline::~Pipeline() = default;

void Pipeline::set_phase_callback(PhaseCallback cb) {
    phase_cb_ = cb;
}

void Pipeline::notify(PipelinePhase phase, const std::string& msg) {
    std::cout << "[" << phase_name(phase) << "] " << msg << std::endl;
    if (phase_cb_) {
        phase_cb_(phase, msg);
    }
}

void Pipeline::log_error(const std::string& source, const std::string& error) {
    current_run_.errors.push_back(source + ": " + error);
    std::cerr << "ERROR [" << source << "] " << error << std::endl;
}

void Pipeline::run(const std::vector<std::string>& sources) {
    // Phase 1: Init
    notify(PipelinePhase::Init, "Initializing pipeline");
    current_run_.run_id = generate_uuid();
    current_run_.started_at = std::chrono::system_clock::now();
    current_run_.status = "running";

    try {
        storage_->init_schema();
        storage_->log_run_start(current_run_);

        // Phase 2: Fetch sources
        fetch_sources(sources);

        // Phase 3: Store raw data
        store_raw();

        // Phase 4: Fuse prices
        fuse_prices();

        // Phase 5: Reconstruct ticks
        reconstruct_ticks();

        // Phase 6: Compute features
        compute_features();

        // Phase 7: Health checks
        health_checks();

        // Phase 8: Generate report
        generate_report();

        // Mark complete
        current_run_.status = "success";
        current_run_.completed_at = std::chrono::system_clock::now();
        storage_->log_run_complete(current_run_);

        // Publish to bus
        bus_->publish_pipeline_complete(current_run_.run_id,
                                        current_run_.sources_fetched,
                                        current_run_.features_computed);

        notify(PipelinePhase::Complete, "Pipeline completed successfully");

    } catch (const std::exception& e) {
        current_run_.status = "failed";
        current_run_.completed_at = std::chrono::system_clock::now();
        log_error("pipeline", e.what());
        storage_->log_run_complete(current_run_);
        throw;
    }
}

void Pipeline::fetch_sources(const std::vector<std::string>& sources) {
    notify(PipelinePhase::FetchSources, "Fetching data sources");

    std::vector<std::unique_ptr<DataSource>> all_sources;
    all_sources.push_back(std::make_unique<YahooSource>(config_));
    all_sources.push_back(std::make_unique<FREDSource>(config_));
    all_sources.push_back(std::make_unique<AlphaVantageSource>(config_));
    all_sources.push_back(std::make_unique<COTSource>(config_));
    all_sources.push_back(std::make_unique<MT5Source>(config_));

    for (auto& source : all_sources) {
        // Filter if specific sources requested
        if (!sources.empty()) {
            bool match = false;
            for (const auto& s : sources) {
                if (s == source->name()) {
                    match = true;
                    break;
                }
            }
            if (!match) continue;
        }

        notify(PipelinePhase::FetchSources, "Fetching: " + source->name());
        auto result = source->fetch();

        if (!result.success) {
            log_error(source->name(), result.error);
            continue;
        }

        // Store in intermediate buffers
        if (!result.bars.empty()) {
            raw_bars_[source->name()] = std::move(result.bars);
        }
        if (!result.macro.empty()) {
            macro_data_.insert(macro_data_.end(),
                              result.macro.begin(), result.macro.end());
        }
        if (!result.cot.empty()) {
            cot_data_.insert(cot_data_.end(),
                            result.cot.begin(), result.cot.end());
        }

        current_run_.sources_fetched++;
        notify(PipelinePhase::FetchSources,
               "Fetched " + source->name() + " (" +
               std::to_string(result.bars.size()) + " bars, " +
               std::to_string(result.macro.size()) + " macro, " +
               std::to_string(result.cot.size()) + " cot)");
    }

    if (raw_bars_.empty()) {
        throw std::runtime_error("No sources fetched successfully");
    }
}

void Pipeline::store_raw() {
    notify(PipelinePhase::StoreRaw, "Storing raw data");

    for (const auto& [source, bars] : raw_bars_) {
        storage_->store_bars(bars);
    }
    storage_->store_macro(macro_data_);
    storage_->store_cot(cot_data_);

    notify(PipelinePhase::StoreRaw, "Stored raw data to database");
}

void Pipeline::fuse_prices() {
    notify(PipelinePhase::FusePrices, "Fusing prices with Kalman filter bank");

    KalmanFilterBank bank(config_.kalman_filters);

    // Build time-aligned observations
    // TODO: Proper time alignment across sources
    // For now: take yahoo as primary timeline
    if (raw_bars_.find("yahoo") == raw_bars_.end()) {
        throw std::runtime_error("Yahoo source required for fusion");
    }

    const auto& yahoo_bars = raw_bars_["yahoo"];
    fused_bars_.reserve(yahoo_bars.size());

    for (const auto& bar : yahoo_bars) {
        // Collect observations at this timestamp
        std::unordered_map<std::string, double> observations;
        for (const auto& [source, bars] : raw_bars_) {
            // Find matching timestamp (TODO: tolerance window)
            for (const auto& src_bar : bars) {
                if (src_bar.timestamp == bar.timestamp) {
                    observations[source] = src_bar.close;
                    break;
                }
            }
        }

        if (observations.empty()) {
            observations["yahoo"] = bar.close;  // fallback
        }

        // Fuse
        auto result = bank.fuse(observations);

        FusedBar fused;
        fused.timestamp = bar.timestamp;
        fused.open = bar.open;
        fused.high = bar.high;
        fused.low = bar.low;
        fused.close = bar.close;
        fused.volume = bar.volume;
        fused.fused_price = result.fused_price;
        fused.fused_confidence = result.confidence;
        fused.source_weights = result.source_weights;
        fused.anomaly_flag = result.anomaly_flag;

        fused_bars_.push_back(fused);
    }

    storage_->store_fused_bars(fused_bars_);
    notify(PipelinePhase::FusePrices,
           "Fused " + std::to_string(fused_bars_.size()) + " bars");
}

void Pipeline::reconstruct_ticks() {
    notify(PipelinePhase::ReconstructTicks, "Reconstructing synthetic ticks");

    // Only first 100 bars
    int n_bars = std::min(100, static_cast<int>(fused_bars_.size()));

    for (int i = 0; i < n_bars; ++i) {
        const auto& bar = fused_bars_[i];

        // Compute end timestamp (assume 1-day bars)
        auto end = bar.timestamp + std::chrono::hours(24);

        auto synth = brownian_bridge(bar.open, bar.high, bar.low, bar.close,
                                      bar.timestamp, end, 100, 0.01);

        for (const auto& st : synth) {
            Tick tick;
            tick.time_msc = std::chrono::duration_cast<std::chrono::milliseconds>(
                st.timestamp.time_since_epoch()).count();
            tick.bid = st.price;
            tick.ask = st.price;  // no spread for synthetic
            tick.mid = st.price;
            tick.spread = 0.0;
            tick.flags = 0;
            tick.volume = 0;
            tick.volume_real = 0;
            tick.collected_at = bar.timestamp;

            synthetic_ticks_.push_back(tick);
        }
    }

    storage_->store_ticks(synthetic_ticks_);
    notify(PipelinePhase::ReconstructTicks,
           "Reconstructed " + std::to_string(synthetic_ticks_.size()) + " synthetic ticks");
}

void Pipeline::compute_features() {
    notify(PipelinePhase::ComputeFeatures, "Computing 400+ features");

    // Extract price vectors
    PriceVec close, high, low, volume;
    for (const auto& bar : fused_bars_) {
        close.push_back(bar.close);
        high.push_back(bar.high);
        low.push_back(bar.low);
        volume.push_back(static_cast<double>(bar.volume));
    }

    // Compute feature sets
    auto price_features = features::compute_price_features(close, high, low, volume,
                                                           config_.feature_windows);
    auto micro_features = features::compute_microstructure_features(close, high, low, volume,
                                                                     config_.feature_windows);

    // TODO: Implement crossasset, macro, cot, regime, calendar features

    // Merge all features
    for (const auto& [name, values] : price_features) {
        features_[name] = values;
    }
    for (const auto& [name, values] : micro_features) {
        features_[name] = values;
    }

    // Validate
    validate_features(features_);

    // Compute IC
    auto returns = log_returns(close, 1);
    auto ic_scores = compute_ic(features_, returns, config_.ic_window);

    // Store
    std::vector<Feature> feature_vec;
    for (const auto& [name, values] : features_) {
        for (size_t i = 0; i < values.size() && i < fused_bars_.size(); ++i) {
            Feature f;
            f.timestamp = fused_bars_[i].timestamp;
            f.name = name;
            f.value = values[i];
            if (ic_scores.find(name) != ic_scores.end()) {
                f.ic_252 = ic_scores[name];
            }
            feature_vec.push_back(f);
        }
    }

    storage_->store_features(feature_vec);
    current_run_.features_computed = features_.size();

    notify(PipelinePhase::ComputeFeatures,
           "Computed " + std::to_string(features_.size()) + " feature types");
}

void Pipeline::health_checks() {
    notify(PipelinePhase::HealthChecks, "Running health checks");

    PipelineMonitor monitor(config_.duckdb_path.string());
    auto staleness = monitor.check_staleness(config_.staleness_hours);
    auto gaps = monitor.detect_gaps("gold_master", 5);

    // Log anomalies
    for (const auto& [source, status] : staleness) {
        if (status.is_stale) {
            Anomaly a;
            a.timestamp = std::chrono::system_clock::now();
            a.type = "staleness";
            a.severity = "medium";
            a.source = source;
            a.description = "Source stale for " + std::to_string(status.age_seconds) + "s";
            storage_->log_anomaly(a);
        }
    }

    notify(PipelinePhase::HealthChecks,
           "Found " + std::to_string(gaps.size()) + " gaps");
}

void Pipeline::generate_report() {
    notify(PipelinePhase::Report, "Generating intelligence report");

    ReportGenerator gen(config_.duckdb_path.string(),
                       config_.ragd_url,
                       config_.reports_dir.string());

    auto report = gen.generate(current_run_.run_id);

    // Send to RAGD
    auto now = std::chrono::system_clock::now();
    auto now_t = std::chrono::system_clock::to_time_t(now);
    char date_buf[16];
    std::strftime(date_buf, sizeof(date_buf), "%Y-%m-%d", std::gmtime(&now_t));

    gen.send_to_ragd(report, date_buf);

    notify(PipelinePhase::Report, "Report generated and sent to RAGD");
}

const PipelineRun& Pipeline::last_run() const {
    return current_run_;
}

} // namespace dominion
