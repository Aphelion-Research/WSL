#pragma once

#include <vector>

namespace hydra {

// Exponential Moving Average
std::vector<float> ema(const std::vector<float>& data, int period);

// Relative Strength Index
std::vector<float> rsi(const std::vector<float>& data, int period);

// Average True Range
std::vector<float> atr(const std::vector<float>& high,
                       const std::vector<float>& low,
                       const std::vector<float>& close,
                       int period);

// Bollinger Bands (returns upper, middle, lower)
struct BollingerBands {
    std::vector<float> upper;
    std::vector<float> middle;
    std::vector<float> lower;
    std::vector<float> width;
};

BollingerBands bollinger_bands(const std::vector<float>& data,
                               int period,
                               float num_std = 2.0f);

// Realized Volatility (close-to-close)
std::vector<float> realized_volatility(const std::vector<float>& data, int period);

} // namespace hydra
