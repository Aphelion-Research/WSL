#pragma once

#include <vector>
#include <cmath>
#include <algorithm>
#include <numeric>
#include <limits>

namespace hydra {

// Rolling mean (point-in-time safe: uses [i-window+1, i])
std::vector<float> rolling_mean(const std::vector<float>& data, int window);

// Rolling std
std::vector<float> rolling_std(const std::vector<float>& data, int window);

// Rolling min
std::vector<float> rolling_min(const std::vector<float>& data, int window);

// Rolling max
std::vector<float> rolling_max(const std::vector<float>& data, int window);

// Rolling z-score
std::vector<float> rolling_zscore(const std::vector<float>& data, int window);

// Rolling skewness
std::vector<float> rolling_skew(const std::vector<float>& data, int window);

// Rolling kurtosis
std::vector<float> rolling_kurt(const std::vector<float>& data, int window);

// Rolling correlation between two series
std::vector<float> rolling_corr(const std::vector<float>& x,
                                const std::vector<float>& y,
                                int window);

} // namespace hydra
