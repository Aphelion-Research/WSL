#include "technical.hpp"
#include <cmath>
#include <algorithm>
#include <limits>

namespace hydra {

constexpr float NAN_F = std::numeric_limits<float>::quiet_NaN();

std::vector<float> ema(const std::vector<float>& data, int period) {
    std::vector<float> result(data.size(), NAN_F);
    if (data.empty() || period < 1) return result;

    float alpha = 2.0f / (period + 1);

    // Find first valid value
    size_t start = 0;
    for (; start < data.size(); ++start) {
        if (!std::isnan(data[start])) {
            result[start] = data[start];
            break;
        }
    }

    // Compute EMA
    for (size_t i = start + 1; i < data.size(); ++i) {
        if (!std::isnan(data[i])) {
            if (std::isnan(result[i - 1])) {
                result[i] = data[i];
            } else {
                result[i] = alpha * data[i] + (1.0f - alpha) * result[i - 1];
            }
        }
    }

    return result;
}

std::vector<float> rsi(const std::vector<float>& data, int period) {
    std::vector<float> result(data.size(), NAN_F);
    if (data.size() < 2 || period < 1) return result;

    // Compute gains and losses
    std::vector<float> gains(data.size(), 0.0f);
    std::vector<float> losses(data.size(), 0.0f);

    for (size_t i = 1; i < data.size(); ++i) {
        if (!std::isnan(data[i]) && !std::isnan(data[i - 1])) {
            float change = data[i] - data[i - 1];
            if (change > 0) {
                gains[i] = change;
            } else {
                losses[i] = -change;
            }
        }
    }

    // Compute average gains and losses
    float avg_gain = 0.0f, avg_loss = 0.0f;
    for (int i = 1; i <= period; ++i) {
        avg_gain += gains[i];
        avg_loss += losses[i];
    }
    avg_gain /= period;
    avg_loss /= period;

    // Compute RSI
    for (size_t i = period; i < data.size(); ++i) {
        if (avg_loss > 0) {
            float rs = avg_gain / avg_loss;
            result[i] = 100.0f - (100.0f / (1.0f + rs));
        } else {
            result[i] = 100.0f;
        }

        // Update averages (smoothed)
        avg_gain = ((avg_gain * (period - 1)) + gains[i]) / period;
        avg_loss = ((avg_loss * (period - 1)) + losses[i]) / period;
    }

    return result;
}

std::vector<float> atr(const std::vector<float>& high,
                       const std::vector<float>& low,
                       const std::vector<float>& close,
                       int period) {
    std::vector<float> result(high.size(), NAN_F);
    if (high.size() != low.size() || high.size() != close.size()) {
        return result;
    }
    if (high.size() < 2 || period < 1) return result;

    // Compute true ranges
    std::vector<float> tr(high.size(), NAN_F);
    for (size_t i = 1; i < high.size(); ++i) {
        if (!std::isnan(high[i]) && !std::isnan(low[i]) && !std::isnan(close[i - 1])) {
            float hl = high[i] - low[i];
            float hc = std::abs(high[i] - close[i - 1]);
            float lc = std::abs(low[i] - close[i - 1]);
            tr[i] = std::max({hl, hc, lc});
        }
    }

    // Compute ATR (smoothed average)
    float sum = 0.0f;
    int count = 0;
    for (int i = 1; i <= period && i < static_cast<int>(tr.size()); ++i) {
        if (!std::isnan(tr[i])) {
            sum += tr[i];
            ++count;
        }
    }

    if (count > 0) {
        result[period] = sum / count;

        for (size_t i = period + 1; i < tr.size(); ++i) {
            if (!std::isnan(tr[i])) {
                result[i] = ((result[i - 1] * (period - 1)) + tr[i]) / period;
            }
        }
    }

    return result;
}

BollingerBands bollinger_bands(const std::vector<float>& data,
                               int period,
                               float num_std) {
    BollingerBands bb;
    bb.upper.resize(data.size(), NAN_F);
    bb.middle.resize(data.size(), NAN_F);
    bb.lower.resize(data.size(), NAN_F);
    bb.width.resize(data.size(), NAN_F);

    if (data.size() < static_cast<size_t>(period)) return bb;

    for (size_t i = period - 1; i < data.size(); ++i) {
        double sum = 0.0;
        double sum_sq = 0.0;
        int count = 0;

        for (int j = 0; j < period; ++j) {
            float val = data[i - j];
            if (!std::isnan(val)) {
                sum += val;
                sum_sq += val * val;
                ++count;
            }
        }

        if (count > 1) {
            double mean = sum / count;
            double variance = (sum_sq / count) - (mean * mean);
            if (variance > 0) {
                double std = std::sqrt(variance);
                bb.middle[i] = static_cast<float>(mean);
                bb.upper[i] = static_cast<float>(mean + num_std * std);
                bb.lower[i] = static_cast<float>(mean - num_std * std);
                bb.width[i] = static_cast<float>(2.0 * num_std * std);
            }
        }
    }

    return bb;
}

std::vector<float> realized_volatility(const std::vector<float>& data, int period) {
    std::vector<float> result(data.size(), NAN_F);
    if (data.size() < 2 || period < 2) return result;

    // Compute log returns
    std::vector<float> returns(data.size(), NAN_F);
    for (size_t i = 1; i < data.size(); ++i) {
        if (!std::isnan(data[i]) && !std::isnan(data[i - 1]) && data[i - 1] > 0) {
            returns[i] = std::log(data[i] / data[i - 1]);
        }
    }

    // Compute rolling std of returns
    for (size_t i = period; i < returns.size(); ++i) {
        double sum = 0.0;
        double sum_sq = 0.0;
        int count = 0;

        for (int j = 0; j < period; ++j) {
            float ret = returns[i - j];
            if (!std::isnan(ret)) {
                sum += ret;
                sum_sq += ret * ret;
                ++count;
            }
        }

        if (count > 1) {
            double mean = sum / count;
            double variance = (sum_sq / count) - (mean * mean);
            if (variance > 0) {
                result[i] = static_cast<float>(std::sqrt(variance));
            }
        }
    }

    return result;
}

} // namespace hydra
