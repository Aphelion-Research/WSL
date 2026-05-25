#include <cmath>
#include "dominion/features.hpp"
#include <cmath>
#include <algorithm>

namespace dominion {

void validate_features(FeatureMap& features, double clip_sigma) {
    for (auto& [name, values] : features) {
        // Replace inf with NaN
        for (auto& v : values) {
            if (std::isinf(v)) v = std::nan("");
        }

        // Compute mean/std (skip NaN)
        double sum = 0.0, sum_sq = 0.0;
        int count = 0;
        for (auto v : values) {
            if (!std::isnan(v)) {
                sum += v;
                sum_sq += v * v;
                ++count;
            }
        }
        if (count == 0) continue;

        double mean = sum / count;
        double variance = (sum_sq / count) - (mean * mean);
        double std = std::sqrt(std::max(0.0, variance));

        // Clip beyond clip_sigma
        double clip_low = mean - clip_sigma * std;
        double clip_high = mean + clip_sigma * std;
        for (auto& v : values) {
            if (!std::isnan(v)) {
                v = std::clamp(v, clip_low, clip_high);
            }
        }
    }
}

std::unordered_map<std::string, double> compute_ic(
    const FeatureMap& features,
    const PriceVec& forward_returns,
    int window
) {
    std::unordered_map<std::string, double> ic_map;

    for (const auto& [name, values] : features) {
        if (values.size() < static_cast<size_t>(window)) continue;

        // Rolling correlation(feature_t, return_{t+1})
        double sum_corr = 0.0;
        int count = 0;

        for (size_t i = 0; i + window < values.size() && i + window < forward_returns.size(); ++i) {
            // Compute correlation for window [i, i+window)
            double sum_x = 0.0, sum_y = 0.0, sum_xy = 0.0, sum_xx = 0.0, sum_yy = 0.0;
            int n = 0;

            for (int j = 0; j < window; ++j) {
                if (i + j + 1 >= forward_returns.size()) break;
                double x = values[i + j];
                double y = forward_returns[i + j + 1];
                if (std::isnan(x) || std::isnan(y)) continue;

                sum_x += x;
                sum_y += y;
                sum_xy += x * y;
                sum_xx += x * x;
                sum_yy += y * y;
                ++n;
            }

            if (n < 10) continue;  // require minimum samples

            double cov = (sum_xy / n) - (sum_x / n) * (sum_y / n);
            double std_x = std::sqrt((sum_xx / n) - (sum_x / n) * (sum_x / n));
            double std_y = std::sqrt((sum_yy / n) - (sum_y / n) * (sum_y / n));

            if (std_x > 1e-9 && std_y > 1e-9) {
                double corr = cov / (std_x * std_y);
                sum_corr += corr;
                ++count;
            }
        }

        if (count > 0) {
            ic_map[name] = sum_corr / count;
        }
    }

    return ic_map;
}

} // namespace dominion
