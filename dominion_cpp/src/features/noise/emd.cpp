#include "dominion/noise.hpp"
#include <algorithm>
#include <cmath>
#include <vector>

namespace dominion::noise {

namespace {

// Find local extrema (peaks and troughs)
void find_extrema(const PriceVec& signal, std::vector<int>& maxima, std::vector<int>& minima) {
    maxima.clear();
    minima.clear();

    for (size_t i = 1; i < signal.size() - 1; ++i) {
        if (signal[i] > signal[i-1] && signal[i] > signal[i+1]) {
            maxima.push_back(i);
        } else if (signal[i] < signal[i-1] && signal[i] < signal[i+1]) {
            minima.push_back(i);
        }
    }
}

// Cubic spline interpolation (simple linear fallback for speed)
PriceVec interpolate_envelope(const PriceVec& signal, const std::vector<int>& extrema) {
    PriceVec envelope(signal.size());

    if (extrema.size() < 2) {
        std::fill(envelope.begin(), envelope.end(), 0.0);
        return envelope;
    }

    for (size_t i = 0; i < signal.size(); ++i) {
        // Find surrounding extrema
        int left = 0, right = extrema.size() - 1;
        for (size_t j = 0; j < extrema.size(); ++j) {
            if (extrema[j] <= static_cast<int>(i)) {
                left = j;
            }
            if (extrema[j] >= static_cast<int>(i)) {
                right = j;
                break;
            }
        }

        if (left == right) {
            envelope[i] = signal[extrema[left]];
        } else {
            // Linear interpolation
            double t = static_cast<double>(i - extrema[left]) / (extrema[right] - extrema[left]);
            envelope[i] = signal[extrema[left]] * (1.0 - t) + signal[extrema[right]] * t;
        }
    }

    return envelope;
}

// Sifting process to extract one IMF
PriceVec sift(PriceVec signal, int max_iterations = 50) {
    PriceVec imf = signal;

    for (int iter = 0; iter < max_iterations; ++iter) {
        std::vector<int> maxima, minima;
        find_extrema(imf, maxima, minima);

        if (maxima.size() < 2 || minima.size() < 2) {
            break; // Cannot continue
        }

        PriceVec upper_env = interpolate_envelope(imf, maxima);
        PriceVec lower_env = interpolate_envelope(imf, minima);

        // Mean envelope
        PriceVec mean_env(imf.size());
        for (size_t i = 0; i < imf.size(); ++i) {
            mean_env[i] = (upper_env[i] + lower_env[i]) / 2.0;
        }

        // New IMF candidate
        PriceVec new_imf(imf.size());
        for (size_t i = 0; i < imf.size(); ++i) {
            new_imf[i] = imf[i] - mean_env[i];
        }

        // Check stopping criterion (mean close to zero)
        double max_diff = 0.0;
        for (size_t i = 0; i < imf.size(); ++i) {
            max_diff = std::max(max_diff, std::abs(new_imf[i] - imf[i]));
        }

        imf = new_imf;

        if (max_diff < 1e-6) {
            break; // Converged
        }
    }

    return imf;
}

} // anonymous namespace

EMDResult compute_emd(const PriceVec& prices, int max_imfs) {
    EMDResult result;
    PriceVec residual = prices;

    for (int i = 0; i < max_imfs; ++i) {
        std::vector<int> maxima, minima;
        find_extrema(residual, maxima, minima);

        if (maxima.size() < 2 || minima.size() < 2) {
            break; // No more IMFs
        }

        PriceVec imf = sift(residual);
        result.imfs.push_back(imf);

        // Subtract IMF from residual
        for (size_t j = 0; j < residual.size(); ++j) {
            residual[j] -= imf[j];
        }

        // Compute dominant frequency (zero-crossing rate)
        int zero_crossings = 0;
        for (size_t j = 1; j < imf.size(); ++j) {
            if ((imf[j] > 0 && imf[j-1] <= 0) || (imf[j] < 0 && imf[j-1] >= 0)) {
                zero_crossings++;
            }
        }
        double frequency = static_cast<double>(zero_crossings) / (2.0 * imf.size());
        result.frequencies.push_back(frequency);

        // Compute energy
        double energy = 0.0;
        for (double val : imf) {
            energy += val * val;
        }
        result.energies.push_back(energy);
    }

    result.residual = residual;

    return result;
}

} // namespace dominion::noise
