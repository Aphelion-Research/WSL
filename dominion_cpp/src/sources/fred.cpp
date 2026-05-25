#include "dominion/sources.hpp"

namespace dominion {

FREDSource::FREDSource(const Config& config) : config_(config) {}

SourceResult FREDSource::fetch() {
    SourceResult result;
    result.source_name = "fred";

    // TODO: Implement FRED API fetch
    // - Use httplib to fetch https://api.stlouisfed.org/fred/series/observations
    // - Loop over config_.fred_series
    // - Parse JSON, handle missing data ('.' values)
    // - Store in result.macro

    result.error = "Not implemented";
    result.success = false;
    return result;
}

} // namespace dominion
