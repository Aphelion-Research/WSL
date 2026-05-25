#include "dominion/features.hpp"

namespace dominion::features {

FeatureMap compute_regime_features(const PriceVec& returns, const PriceVec& volatility,
                                   const PriceVec& volume,
                                   const std::vector<Timestamp>& timestamps) {
    FeatureMap features;

    // TODO: Time-based micro regime (london/ny/asian/overlap/dead_zone)
    // HMM regimes via external Python bridge or native implementation

    return features;
}

} // namespace dominion::features
