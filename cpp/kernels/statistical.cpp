#include "statistical.hpp"
#include <cmath>
#include <algorithm>
#include <numeric>
#include <limits>

namespace hydra {

constexpr float NAN_F = std::numeric_limits<float>::quiet_NaN();

std::vector<float> autocorr(const std::vector<float>& data, int lag) {
    std::vector<float> result(data.size(), NAN_F);
    if (lag < 1 || static_cast<size_t>(lag) >= data.size()) return result;

    // Compute mean
    double sum = 0.0;
    int count = 0;
    for (float val : data) {
        if (!std::isnan(val)) {
            sum += val;
            ++count;
        }
    }
    if (count < 2) return result;
    double mean = sum / count;

    // Compute variance and autocovariance
    for (size_t i = lag; i < data.size(); ++i) {
        if (!std::isnan(data[i]) && !std::isnan(data[i - lag])) {
            // Compute local autocorrelation (using all data up to i)
            double sum_xx = 0.0, sum_yy = 0.0, sum_xy = 0.0;
            int n = 0;

            for (size_t j = lag; j <= i; ++j) {
                if (!std::isnan(data[j]) && !std::isnan(data[j - lag])) {
                    double x = data[j - lag] - mean;
                    double y = data[j] - mean;
                    sum_xx += x * x;
                    sum_yy += y * y;
                    sum_xy += x * y;
                    ++n;
                }
            }

            if (n > 0 && sum_xx > 0 && sum_yy > 0) {
                result[i] = static_cast<float>(sum_xy / std::sqrt(sum_xx * sum_yy));
            }
        }
    }

    return result;
}

std::vector<float> rolling_autocorr(const std::vector<float>& data,
                                    int window,
                                    int lag) {
    std::vector<float> result(data.size(), NAN_F);
    if (lag < 1 || window < lag + 2) return result;

    for (size_t i = window - 1; i < data.size(); ++i) {
        // Compute autocorr within window [i-window+1, i]
        std::vector<double> vals;
        vals.reserve(window);

        for (int j = 0; j < window; ++j) {
            float val = data[i - j];
            if (!std::isnan(val)) {
                vals.push_back(val);
            }
        }

        if (vals.size() > static_cast<size_t>(lag + 1)) {
            // Reverse to chronological order
            std::reverse(vals.begin(), vals.end());

            double mean = std::accumulate(vals.begin(), vals.end(), 0.0) / vals.size();

            double sum_xx = 0.0, sum_yy = 0.0, sum_xy = 0.0;
            size_t n = 0;

            for (size_t j = lag; j < vals.size(); ++j) {
                double x = vals[j - lag] - mean;
                double y = vals[j] - mean;
                sum_xx += x * x;
                sum_yy += y * y;
                sum_xy += x * y;
                ++n;
            }

            if (n > 0 && sum_xx > 0 && sum_yy > 0) {
                result[i] = static_cast<float>(sum_xy / std::sqrt(sum_xx * sum_yy));
            }
        }
    }

    return result;
}

std::vector<float> rolling_quantile(const std::vector<float>& data,
                                    int window,
                                    float q) {
    std::vector<float> result(data.size(), NAN_F);
    if (q < 0.0f || q > 1.0f) return result;

    for (size_t i = window - 1; i < data.size(); ++i) {
        std::vector<float> vals;
        vals.reserve(window);

        for (int j = 0; j < window; ++j) {
            float val = data[i - j];
            if (!std::isnan(val)) {
                vals.push_back(val);
            }
        }

        if (!vals.empty()) {
            std::sort(vals.begin(), vals.end());
            float pos = q * (vals.size() - 1);
            size_t idx = static_cast<size_t>(pos);

            if (idx >= vals.size() - 1) {
                result[i] = vals.back();
            } else {
                // Linear interpolation
                float frac = pos - idx;
                result[i] = vals[idx] + frac * (vals[idx + 1] - vals[idx]);
            }
        }
    }

    return result;
}

} // namespace hydra
