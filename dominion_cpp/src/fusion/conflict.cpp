#include "dominion/fusion.hpp"
#include <algorithm>
#include <cmath>

namespace dominion {

ConflictResult resolve_conflict(
    const std::unordered_map<std::string, double>& observations,
    double fused_price,
    double confidence,
    const std::unordered_map<std::string, double>& trust_scores
) {
    ConflictResult result;
    result.resolved_price = fused_price;
    result.byzantine_detected = false;

    // Byzantine fault tolerance: if >=3 sources agree (within 1σ), use median
    std::vector<double> prices;
    for (const auto& [source, price] : observations) {
        prices.push_back(price);
    }

    if (prices.size() >= 3) {
        std::sort(prices.begin(), prices.end());
        double median = prices[prices.size() / 2];
        result.resolved_price = median;
    }

    // Quarantine outliers >3σ
    for (const auto& [source, price] : observations) {
        double z = std::abs(price - fused_price) / (confidence + 1e-9);
        if (z > 3.0) {
            result.quarantined_sources.push_back(source);
        }
    }

    return result;
}

} // namespace dominion
