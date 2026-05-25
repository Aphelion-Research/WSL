#include "dominion/sources.hpp"

namespace dominion {

AlphaVantageSource::AlphaVantageSource(const Config& config) : config_(config) {
    cache_path_ = "/tmp/av_gld_cache.json";
}

SourceResult AlphaVantageSource::fetch() {
    SourceResult result;
    result.source_name = "alphavantage";
    // TODO: Implement with cache (23h TTL), rate limiting (13s delay)
    result.error = "Not implemented";
    result.success = false;
    return result;
}

} // namespace dominion
