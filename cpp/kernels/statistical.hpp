#pragma once

#include <vector>

namespace hydra {

// Autocorrelation at given lag
std::vector<float> autocorr(const std::vector<float>& data, int lag);

// Rolling autocorrelation
std::vector<float> rolling_autocorr(const std::vector<float>& data,
                                    int window,
                                    int lag);

// Quantile computation
std::vector<float> rolling_quantile(const std::vector<float>& data,
                                    int window,
                                    float q);

} // namespace hydra
