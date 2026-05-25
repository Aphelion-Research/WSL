#include <cmath>
#include <cmath>
#include "dominion/features.hpp"

namespace dominion::features {

FeatureMap compute_microstructure_features(const PriceVec& close, const PriceVec& high,
                                           const PriceVec& low, const PriceVec& volume,
                                           const std::vector<int>& windows) {
    FeatureMap features;

    // Amihud illiquidity
    auto ret = log_returns(close, 1);
    PriceVec amihud(close.size(), std::nan(""));
    for (size_t i = 1; i < close.size(); ++i) {
        if (volume[i] > 1e-9) {
            amihud[i] = std::abs(ret[i]) / volume[i];
        }
    }
    features["amihud_illiquidity"] = amihud;

    // Realized variance (sum of squared returns)
    for (int w : windows) {
        PriceVec rv(close.size(), std::nan(""));
        for (size_t i = w; i < close.size(); ++i) {
            double sum_sq = 0.0;
            for (int j = 0; j < w; ++j) {
                sum_sq += ret[i - j] * ret[i - j];
            }
            rv[i] = sum_sq;
        }
        features["realized_variance_" + std::to_string(w)] = rv;
    }

    // TODO: Roll spread, Corwin-Schultz, Kyle's lambda, VPIN, bipower variation

    return features;
}

} // namespace dominion::features
