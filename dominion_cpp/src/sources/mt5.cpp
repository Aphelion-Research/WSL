#include "dominion/sources.hpp"

namespace dominion {

MT5Source::MT5Source(const Config& config) : config_(config) {}

SourceResult MT5Source::fetch() {
    SourceResult result;
    result.source_name = "mt5";
    // TODO: Call domdata CLI via subprocess, parse JSON output
    result.error = "Not implemented";
    result.success = false;
    return result;
}

} // namespace dominion
