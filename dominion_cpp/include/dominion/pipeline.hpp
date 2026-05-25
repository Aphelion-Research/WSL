#pragma once

#include "dominion/config.hpp"
#include "dominion/types.hpp"

#include <functional>
#include <memory>
#include <string>
#include <vector>

namespace dominion {

class Storage;
class BusPublisher;

enum class PipelinePhase {
    Init,
    FetchSources,
    StoreRaw,
    FusePrices,
    ReconstructTicks,
    ComputeFeatures,
    HealthChecks,
    Report,
    Complete,
};

using PhaseCallback = std::function<void(PipelinePhase, const std::string&)>;

class Pipeline {
public:
    explicit Pipeline(Config config);
    ~Pipeline();

    void run(const std::vector<std::string>& sources = {});
    void set_phase_callback(PhaseCallback cb);

    const PipelineRun& last_run() const;

private:
    void fetch_sources(const std::vector<std::string>& sources);
    void store_raw();
    void fuse_prices();
    void reconstruct_ticks();
    void compute_features();
    void health_checks();
    void generate_report();

    void notify(PipelinePhase phase, const std::string& msg);
    void log_error(const std::string& source, const std::string& error);

    Config config_;
    std::unique_ptr<Storage> storage_;
    std::unique_ptr<BusPublisher> bus_;
    PipelineRun current_run_;
    PhaseCallback phase_cb_;

    // Intermediate state
    std::unordered_map<std::string, std::vector<Bar>> raw_bars_;
    std::vector<MacroData> macro_data_;
    std::vector<COTData> cot_data_;
    std::vector<FusedBar> fused_bars_;
    std::vector<Tick> synthetic_ticks_;
    FeatureMap features_;
};

} // namespace dominion
