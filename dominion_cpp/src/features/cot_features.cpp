#include "dominion/features.hpp"

namespace dominion::features {

FeatureMap compute_cot_features(const std::vector<COTData>& cot,
                                const std::vector<int>& windows) {
    FeatureMap features;

    // TODO: Net commercial percentile, speculator sentiment percentile,
    // momentum, hedger ratio, spec concentration

    return features;
}

} // namespace dominion::features
