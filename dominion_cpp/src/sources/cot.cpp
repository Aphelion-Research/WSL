#include "dominion/sources.hpp"

namespace dominion {

COTSource::COTSource(const Config& config) : config_(config) {}

SourceResult COTSource::fetch() {
    SourceResult result;
    result.source_name = "cot";
    // TODO: Download ZIP, extract Excel, parse gold code 088691
    result.error = "Not implemented";
    result.success = false;
    return result;
}

} // namespace dominion
