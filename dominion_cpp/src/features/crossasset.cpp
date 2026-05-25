#include "dominion/features.hpp"

namespace dominion::features {

FeatureMap compute_crossasset_features(const PriceVec& gold_returns,
                                       const std::unordered_map<std::string, PriceVec>& macro_series,
                                       const std::vector<int>& windows) {
    FeatureMap features;

    // TODO: Rolling correlation, beta, lead-lag, Granger causality, partial correlation

    return features;
}

} // namespace dominion::features
