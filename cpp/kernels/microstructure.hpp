#pragma once

#include <vector>

namespace hydra {

// Candle body size (close - open)
std::vector<float> candle_body(const std::vector<float>& open,
                               const std::vector<float>& close);

// Upper wick size (high - max(open, close))
std::vector<float> candle_upper_wick(const std::vector<float>& open,
                                     const std::vector<float>& high,
                                     const std::vector<float>& close);

// Lower wick size (min(open, close) - low)
std::vector<float> candle_lower_wick(const std::vector<float>& open,
                                     const std::vector<float>& low,
                                     const std::vector<float>& close);

// Candle range (high - low)
std::vector<float> candle_range(const std::vector<float>& high,
                                const std::vector<float>& low);

// Body ratio (body / range)
std::vector<float> candle_body_ratio(const std::vector<float>& open,
                                     const std::vector<float>& high,
                                     const std::vector<float>& low,
                                     const std::vector<float>& close);

// Close location within range [0, 1]
std::vector<float> candle_close_loc(const std::vector<float>& high,
                                    const std::vector<float>& low,
                                    const std::vector<float>& close);

} // namespace hydra
