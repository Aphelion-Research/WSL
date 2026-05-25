#include "dominion/noise.hpp"
#include <cmath>
#include <algorithm>

namespace dominion::noise {

namespace {

// Daubechies 4 wavelet coefficients
const double db4_dec_lo[] = {0.6830127, 1.1830127, 0.3169873, -0.1830127};
const double db4_dec_hi[] = {-0.1830127, -0.3169873, 1.1830127, -0.6830127};
const int db4_len = 4;

// Convolution with wavelet filter
PriceVec convolve(const PriceVec& signal, const double* filter, int filter_len, int stride) {
    int out_len = (signal.size() + stride - 1) / stride;
    PriceVec result(out_len, 0.0);

    for (int i = 0; i < out_len; ++i) {
        int pos = i * stride;
        for (int j = 0; j < filter_len && pos + j < static_cast<int>(signal.size()); ++j) {
            result[i] += signal[pos + j] * filter[j];
        }
    }

    return result;
}

} // anonymous namespace

WaveletResult compute_wavelet_packet(const PriceVec& prices, int levels, const std::string& wavelet) {
    WaveletResult result;

    // Only db4 supported for now
    const double* lo_filter = db4_dec_lo;
    const double* hi_filter = db4_dec_hi;
    const int filter_len = db4_len;

    PriceVec signal = prices;

    for (int level = 0; level < levels; ++level) {
        // Low-pass (approximation)
        PriceVec approx = convolve(signal, lo_filter, filter_len, 2);
        result.approx.push_back(approx);

        // High-pass (detail)
        PriceVec detail = convolve(signal, hi_filter, filter_len, 2);
        result.details.push_back(detail);

        // Compute energy of detail coefficients
        double energy = 0.0;
        for (double val : detail) {
            energy += val * val;
        }
        result.energies.push_back(energy);

        // Continue decomposition on approximation
        signal = approx;

        if (signal.size() < static_cast<size_t>(filter_len)) {
            break; // Cannot decompose further
        }
    }

    return result;
}

} // namespace dominion::noise
