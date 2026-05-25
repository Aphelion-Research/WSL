#include "dominion/features.hpp"
#include <cmath>
#include <algorithm>
#include <numeric>

namespace dominion {

PriceVec rolling_mean(const PriceVec& data, int window) {
    PriceVec result(data.size(), std::nan(""));
    if (data.size() < static_cast<size_t>(window)) return result;

    double sum = 0.0;
    for (int i = 0; i < window; ++i) sum += data[i];

    for (size_t i = window; i < data.size(); ++i) {
        result[i] = sum / window;
        sum += data[i] - data[i - window];
    }
    return result;
}

PriceVec rolling_std(const PriceVec& data, int window) {
    PriceVec result(data.size(), std::nan(""));
    if (data.size() < static_cast<size_t>(window)) return result;

    for (size_t i = window; i < data.size(); ++i) {
        double sum = 0.0, sum_sq = 0.0;
        for (int j = 0; j < window; ++j) {
            double v = data[i - j];
            sum += v;
            sum_sq += v * v;
        }
        double mean = sum / window;
        double variance = (sum_sq / window) - (mean * mean);
        result[i] = std::sqrt(std::max(0.0, variance));
    }
    return result;
}

PriceVec rolling_skew(const PriceVec& data, int window) {
    PriceVec result(data.size(), std::nan(""));
    // TODO: Implement skewness calculation
    return result;
}

PriceVec rolling_kurtosis(const PriceVec& data, int window) {
    PriceVec result(data.size(), std::nan(""));
    // TODO: Implement kurtosis calculation
    return result;
}

PriceVec rolling_correlation(const PriceVec& x, const PriceVec& y, int window) {
    PriceVec result(std::min(x.size(), y.size()), std::nan(""));
    // TODO: Implement rolling correlation
    return result;
}

PriceVec ema(const PriceVec& data, int period) {
    PriceVec result(data.size(), std::nan(""));
    if (data.empty()) return result;

    double alpha = 2.0 / (period + 1.0);
    result[0] = data[0];

    for (size_t i = 1; i < data.size(); ++i) {
        result[i] = alpha * data[i] + (1.0 - alpha) * result[i - 1];
    }
    return result;
}

PriceVec diff(const PriceVec& data, int lag) {
    PriceVec result(data.size(), std::nan(""));
    for (size_t i = lag; i < data.size(); ++i) {
        result[i] = data[i] - data[i - lag];
    }
    return result;
}

PriceVec pct_change(const PriceVec& data, int lag) {
    PriceVec result(data.size(), std::nan(""));
    for (size_t i = lag; i < data.size(); ++i) {
        if (std::abs(data[i - lag]) > 1e-9) {
            result[i] = (data[i] - data[i - lag]) / data[i - lag];
        }
    }
    return result;
}

PriceVec log_returns(const PriceVec& data, int lag) {
    PriceVec result(data.size(), std::nan(""));
    for (size_t i = lag; i < data.size(); ++i) {
        if (data[i - lag] > 0.0 && data[i] > 0.0) {
            result[i] = std::log(data[i] / data[i - lag]);
        }
    }
    return result;
}

PriceVec cummax(const PriceVec& data) {
    PriceVec result(data.size(), std::nan(""));
    if (data.empty()) return result;

    double max_val = data[0];
    result[0] = max_val;

    for (size_t i = 1; i < data.size(); ++i) {
        max_val = std::max(max_val, data[i]);
        result[i] = max_val;
    }
    return result;
}

PriceVec drawdown(const PriceVec& data) {
    auto max_vals = cummax(data);
    PriceVec result(data.size(), std::nan(""));

    for (size_t i = 0; i < data.size(); ++i) {
        if (std::abs(max_vals[i]) > 1e-9) {
            result[i] = (data[i] - max_vals[i]) / max_vals[i];
        }
    }
    return result;
}

} // namespace dominion
