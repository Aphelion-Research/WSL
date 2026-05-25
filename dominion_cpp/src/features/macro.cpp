#include "dominion/features.hpp"

namespace dominion::features {

FeatureMap compute_macro_features(const PriceVec& gold_close,
                                  const std::unordered_map<std::string, PriceVec>& macro_series,
                                  const std::vector<std::string>& fomc_dates) {
    FeatureMap features;

    // TODO: Real yield, yield curve, DXY momentum, CPI, Fed proximity, real gold price

    return features;
}

} // namespace dominion::features
