#include "dominion/features.hpp"

namespace dominion::features {

FeatureMap compute_price_features(const PriceVec& close, const PriceVec& high,
                                  const PriceVec& low, const PriceVec& volume,
                                  const std::vector<int>& windows) {
    FeatureMap features;

    // Returns (simple & log) at all windows
    for (int w : windows) {
        features["simple_return_" + std::to_string(w)] = pct_change(close, w);
        features["log_return_" + std::to_string(w)] = log_returns(close, w);
    }

    // Rolling statistics
    for (int w : windows) {
        features["rolling_mean_" + std::to_string(w)] = rolling_mean(close, w);
        features["rolling_std_" + std::to_string(w)] = rolling_std(close, w);
    }

    // Sharpe (annualized)
    for (int w : windows) {
        auto ret = log_returns(close, 1);
        auto mean_ret = rolling_mean(ret, w);
        auto std_ret = rolling_std(ret, w);

        PriceVec sharpe(close.size(), std::nan(""));
        for (size_t i = 0; i < close.size(); ++i) {
            if (std_ret[i] > 1e-9) {
                sharpe[i] = (mean_ret[i] / std_ret[i]) * std::sqrt(252.0);  // annualize
            }
        }
        features["sharpe_" + std::to_string(w)] = sharpe;
    }

    // Drawdown
    for (int w : windows) {
        auto dd = drawdown(close);
        features["drawdown_" + std::to_string(w)] = dd;
    }

    // Z-score
    for (int w : windows) {
        auto mean = rolling_mean(close, w);
        auto std = rolling_std(close, w);
        PriceVec zscore(close.size(), std::nan(""));
        for (size_t i = 0; i < close.size(); ++i) {
            if (std[i] > 1e-9) {
                zscore[i] = (close[i] - mean[i]) / std[i];
            }
        }
        features["zscore_" + std::to_string(w)] = zscore;
    }

    // TODO: Hurst, autocorr, fractional differentiation, ADF

    return features;
}

} // namespace dominion::features
