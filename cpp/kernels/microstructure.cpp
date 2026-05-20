#include "microstructure.hpp"
#include <cmath>
#include <algorithm>
#include <limits>

namespace hydra {

constexpr float NAN_F = std::numeric_limits<float>::quiet_NaN();

std::vector<float> candle_body(const std::vector<float>& open,
                               const std::vector<float>& close) {
    std::vector<float> result(open.size(), NAN_F);
    for (size_t i = 0; i < open.size(); ++i) {
        if (!std::isnan(open[i]) && !std::isnan(close[i])) {
            result[i] = close[i] - open[i];
        }
    }
    return result;
}

std::vector<float> candle_upper_wick(const std::vector<float>& open,
                                     const std::vector<float>& high,
                                     const std::vector<float>& close) {
    std::vector<float> result(open.size(), NAN_F);
    for (size_t i = 0; i < open.size(); ++i) {
        if (!std::isnan(open[i]) && !std::isnan(high[i]) && !std::isnan(close[i])) {
            result[i] = high[i] - std::max(open[i], close[i]);
        }
    }
    return result;
}

std::vector<float> candle_lower_wick(const std::vector<float>& open,
                                     const std::vector<float>& low,
                                     const std::vector<float>& close) {
    std::vector<float> result(open.size(), NAN_F);
    for (size_t i = 0; i < open.size(); ++i) {
        if (!std::isnan(open[i]) && !std::isnan(low[i]) && !std::isnan(close[i])) {
            result[i] = std::min(open[i], close[i]) - low[i];
        }
    }
    return result;
}

std::vector<float> candle_range(const std::vector<float>& high,
                                const std::vector<float>& low) {
    std::vector<float> result(high.size(), NAN_F);
    for (size_t i = 0; i < high.size(); ++i) {
        if (!std::isnan(high[i]) && !std::isnan(low[i])) {
            result[i] = high[i] - low[i];
        }
    }
    return result;
}

std::vector<float> candle_body_ratio(const std::vector<float>& open,
                                     const std::vector<float>& high,
                                     const std::vector<float>& low,
                                     const std::vector<float>& close) {
    std::vector<float> result(open.size(), NAN_F);
    for (size_t i = 0; i < open.size(); ++i) {
        if (!std::isnan(open[i]) && !std::isnan(high[i]) &&
            !std::isnan(low[i]) && !std::isnan(close[i])) {
            float range = high[i] - low[i];
            if (range > 0) {
                float body = std::abs(close[i] - open[i]);
                result[i] = body / range;
            }
        }
    }
    return result;
}

std::vector<float> candle_close_loc(const std::vector<float>& high,
                                    const std::vector<float>& low,
                                    const std::vector<float>& close) {
    std::vector<float> result(high.size(), NAN_F);
    for (size_t i = 0; i < high.size(); ++i) {
        if (!std::isnan(high[i]) && !std::isnan(low[i]) && !std::isnan(close[i])) {
            float range = high[i] - low[i];
            if (range > 0) {
                result[i] = (close[i] - low[i]) / range;
            } else {
                result[i] = 0.5f;  // Close in middle if no range
            }
        }
    }
    return result;
}

} // namespace hydra
