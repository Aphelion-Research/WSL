#include "dominion/noise.hpp"
#include "dominion/features.hpp"
#include <cmath>
#include <algorithm>

namespace dominion::noise {

FeatureMap extract_noise_features(const SSAResult& ssa, const EMDResult& emd, const VMDResult& vmd) {
    FeatureMap features;
    const int N = ssa.trend.size();

    // SSA features
    if (!ssa.singular_values.empty()) {
        features["ssa_first_sv"] = PriceVec(N, ssa.singular_values[0]);
        features["ssa_explained_var_ratio"] = PriceVec(N, ssa.explained_variance.empty() ? 0.0 : ssa.explained_variance[0]);

        // Trend strength
        PriceVec trend_strength(N);
        for (int i = 0; i < N; ++i) {
            double trend_power = ssa.trend[i] * ssa.trend[i];
            double noise_power = ssa.noise[i] * ssa.noise[i];
            trend_strength[i] = trend_power / (trend_power + noise_power + 1e-12);
        }
        features["ssa_trend_strength"] = trend_strength;

        // Export trend and noise
        features["ssa_trend"] = ssa.trend;
        features["ssa_noise"] = ssa.noise;
    }

    // EMD features
    for (size_t i = 0; i < emd.imfs.size(); ++i) {
        features["emd_imf" + std::to_string(i) + "_energy"] = PriceVec(N, emd.energies[i]);
        features["emd_imf" + std::to_string(i) + "_freq"] = PriceVec(N, emd.frequencies[i]);

        // Mode itself (first 3 IMFs only to save features)
        if (i < 3) {
            features["emd_imf" + std::to_string(i)] = emd.imfs[i];
        }
    }

    // Energy ratio (high freq vs low freq)
    if (emd.energies.size() >= 2) {
        double high_freq_energy = 0.0;
        double low_freq_energy = 0.0;

        for (size_t i = 0; i < std::min(size_t(3), emd.energies.size()); ++i) {
            high_freq_energy += emd.energies[i];
        }
        for (size_t i = 3; i < emd.energies.size(); ++i) {
            low_freq_energy += emd.energies[i];
        }

        double ratio = high_freq_energy / (low_freq_energy + 1e-12);
        features["emd_hf_lf_ratio"] = PriceVec(N, ratio);
    }

    // VMD features
    for (size_t i = 0; i < vmd.modes.size(); ++i) {
        features["vmd_mode" + std::to_string(i) + "_center_freq"] = PriceVec(N, vmd.center_frequencies[i]);
        features["vmd_mode" + std::to_string(i) + "_bandwidth"] = PriceVec(N, vmd.bandwidths[i]);

        // Mode itself (first 3 only)
        if (i < 3) {
            features["vmd_mode" + std::to_string(i)] = vmd.modes[i];
        }
    }

    return features;
}

PriceVec detect_mode_crossings(const std::vector<PriceVec>& modes, int window) {
    if (modes.empty()) {
        return PriceVec();
    }

    const int N = modes[0].size();
    PriceVec crossings(N, 0.0);

    // Detect when dominant mode changes
    for (int i = window; i < N; ++i) {
        // Find dominant mode in current window
        int dominant_current = 0;
        double max_energy_current = 0.0;

        for (size_t m = 0; m < modes.size(); ++m) {
            double energy = 0.0;
            for (int j = i - window; j < i; ++j) {
                energy += modes[m][j] * modes[m][j];
            }
            if (energy > max_energy_current) {
                max_energy_current = energy;
                dominant_current = m;
            }
        }

        // Find dominant mode in previous window
        int dominant_prev = 0;
        double max_energy_prev = 0.0;

        for (size_t m = 0; m < modes.size(); ++m) {
            double energy = 0.0;
            for (int j = i - 2 * window; j < i - window && j >= 0; ++j) {
                energy += modes[m][j] * modes[m][j];
            }
            if (energy > max_energy_prev) {
                max_energy_prev = energy;
                dominant_prev = m;
            }
        }

        // Crossing = change in dominant mode
        if (dominant_current != dominant_prev) {
            crossings[i] = 1.0;
        }
    }

    return crossings;
}

PriceVec compute_snr(const PriceVec& signal, const PriceVec& noise, int window) {
    const int N = signal.size();
    PriceVec snr(N, std::nan(""));

    for (int i = window; i < N; ++i) {
        double signal_power = 0.0;
        double noise_power = 0.0;

        for (int j = i - window; j < i; ++j) {
            signal_power += signal[j] * signal[j];
            noise_power += noise[j] * noise[j];
        }

        if (noise_power > 1e-12) {
            snr[i] = 10.0 * std::log10(signal_power / noise_power);
        }
    }

    return snr;
}

PriceVec adaptive_denoise(const PriceVec& prices, int window) {
    const int N = prices.size();
    PriceVec denoised(N, std::nan(""));

    for (int i = window; i < N; ++i) {
        // Estimate signal variance (simplified Wiener filter)
        double mean = 0.0;
        for (int j = i - window; j < i; ++j) {
            mean += prices[j];
        }
        mean /= window;

        double variance = 0.0;
        for (int j = i - window; j < i; ++j) {
            variance += (prices[j] - mean) * (prices[j] - mean);
        }
        variance /= window;

        // Estimate noise variance (from high-freq differences)
        double noise_var = 0.0;
        for (int j = i - window + 1; j < i; ++j) {
            double diff = prices[j] - prices[j - 1];
            noise_var += diff * diff;
        }
        noise_var /= (2.0 * (window - 1));

        // Wiener gain
        double signal_var = std::max(0.0, variance - noise_var);
        double gain = signal_var / (signal_var + noise_var + 1e-12);

        denoised[i] = mean + gain * (prices[i - 1] - mean);
    }

    return denoised;
}

} // namespace dominion::noise
