#include "dominion/features.hpp"
#include <cmath>
#include <algorithm>
#include <complex>
#include <numeric>

namespace dominion::features {

// Feature #66: Empirical Mode Decomposition (simplified IMF extraction)
// Full EMD requires iterative sifting; here we use band-pass filters as IMF proxies
FeatureMap compute_emd_features(const PriceVec& prices) {
    FeatureMap result;
    if (prices.size() < 100) return result;

    size_t n = prices.size();

    // IMF 1: High-frequency (1-5 bar oscillations) via diff-of-EMAs
    auto ema_fast = ema(prices, 2);
    auto ema_med = ema(prices, 5);
    PriceVec imf1(n);
    for (size_t i = 0; i < n; ++i) {
        imf1[i] = ema_fast[i] - ema_med[i];
    }
    result["emd_imf1_hf"] = imf1;

    // IMF 2: Medium-frequency (5-20 bar oscillations)
    auto ema_med2 = ema(prices, 20);
    PriceVec imf2(n);
    for (size_t i = 0; i < n; ++i) {
        imf2[i] = ema_med[i] - ema_med2[i];
    }
    result["emd_imf2_mf"] = imf2;

    // IMF 3: Low-frequency (20-60 bar oscillations)
    auto ema_slow = ema(prices, 60);
    PriceVec imf3(n);
    for (size_t i = 0; i < n; ++i) {
        imf3[i] = ema_med2[i] - ema_slow[i];
    }
    result["emd_imf3_lf"] = imf3;

    // Residual (trend)
    result["emd_residual_trend"] = ema_slow;

    // IMF energy (variance over rolling window)
    for (int imf_idx = 1; imf_idx <= 3; ++imf_idx) {
        std::string imf_name = "emd_imf" + std::to_string(imf_idx);
        const auto& imf = (imf_idx == 1) ? imf1 : (imf_idx == 2) ? imf2 : imf3;

        PriceVec energy(n, std::nan(""));
        int window = 60;
        for (int i = window; i < static_cast<int>(n); ++i) {
            double sum_sq = 0.0;
            for (int t = i - window; t < i; ++t) {
                sum_sq += imf[t] * imf[t];
            }
            energy[i] = sum_sq / window;
        }
        result[imf_name + "_energy"] = energy;
    }

    // Instantaneous frequency (zero-crossing rate proxy)
    for (int imf_idx = 1; imf_idx <= 3; ++imf_idx) {
        const auto& imf = (imf_idx == 1) ? imf1 : (imf_idx == 2) ? imf2 : imf3;

        PriceVec inst_freq(n, std::nan(""));
        int window = 60;
        for (int i = window; i < static_cast<int>(n); ++i) {
            int crossings = 0;
            for (int t = i - window + 1; t < i; ++t) {
                if ((imf[t-1] < 0 && imf[t] >= 0) || (imf[t-1] >= 0 && imf[t] < 0)) {
                    crossings++;
                }
            }
            inst_freq[i] = static_cast<double>(crossings) / window;
        }
        result["emd_imf" + std::to_string(imf_idx) + "_inst_freq"] = inst_freq;
    }

    return result;
}

// Feature #67: Hilbert-Huang Transform (instantaneous phase/amplitude)
FeatureMap compute_hilbert_features(const PriceVec& prices) {
    FeatureMap result;
    if (prices.size() < 100) return result;

    size_t n = prices.size();

    // Simplified Hilbert transform via 90-degree phase shift approximation
    // H(x[n]) ≈ -x[n-1] + x[n+1] (discrete Hilbert transform approximation)

    PriceVec hilbert(n, std::nan(""));
    for (int i = 1; i < static_cast<int>(n) - 1; ++i) {
        hilbert[i] = -prices[i-1] + prices[i+1];
    }

    // Instantaneous amplitude: sqrt(x^2 + H(x)^2)
    PriceVec inst_amplitude(n, std::nan(""));
    for (int i = 1; i < static_cast<int>(n) - 1; ++i) {
        inst_amplitude[i] = std::sqrt(prices[i] * prices[i] + hilbert[i] * hilbert[i]);
    }
    result["hilbert_inst_amplitude"] = inst_amplitude;

    // Instantaneous phase: atan2(H(x), x)
    PriceVec inst_phase(n, std::nan(""));
    for (int i = 1; i < static_cast<int>(n) - 1; ++i) {
        inst_phase[i] = std::atan2(hilbert[i], prices[i]);
    }
    result["hilbert_inst_phase"] = inst_phase;

    // Phase derivative (instantaneous frequency)
    PriceVec inst_freq(n, std::nan(""));
    for (int i = 2; i < static_cast<int>(n) - 1; ++i) {
        inst_freq[i] = inst_phase[i] - inst_phase[i-1];
        // Wrap to [-π, π]
        while (inst_freq[i] > M_PI) inst_freq[i] -= 2 * M_PI;
        while (inst_freq[i] < -M_PI) inst_freq[i] += 2 * M_PI;
    }
    result["hilbert_inst_frequency"] = inst_freq;

    // Amplitude envelope trend
    auto amp_trend = rolling_mean(inst_amplitude, 60);
    result["hilbert_amplitude_trend"] = amp_trend;

    return result;
}

// Feature #69: Singular Spectrum Analysis (SSA) - trend/cycle decomposition
FeatureMap compute_ssa_features(const PriceVec& prices, int window_length, int n_components) {
    FeatureMap result;
    if (prices.size() < static_cast<size_t>(window_length * 2)) return result;

    size_t n = prices.size();
    int K = n - window_length + 1;  // Number of lagged vectors

    // Build trajectory matrix (Hankel matrix)
    std::vector<std::vector<double>> X(window_length, std::vector<double>(K));
    for (int i = 0; i < window_length; ++i) {
        for (int j = 0; j < K; ++j) {
            X[i][j] = prices[i + j];
        }
    }

    // Compute covariance matrix C = X * X^T (simplified: use row means as proxy)
    // Full implementation requires SVD; here we use simple moving average decomposition

    // Component 1: Slow trend (window_length/2 MA)
    auto trend = rolling_mean(prices, window_length / 2);
    result["ssa_trend"] = trend;

    // Component 2: Detrended signal
    PriceVec detrended(n);
    for (size_t i = 0; i < n; ++i) {
        detrended[i] = prices[i] - trend[i];
    }

    // Component 3: Oscillatory (band-pass via diff of MAs)
    auto ma_short = rolling_mean(detrended, 10);
    auto ma_long = rolling_mean(detrended, 30);
    PriceVec oscillatory(n);
    for (size_t i = 0; i < n; ++i) {
        oscillatory[i] = ma_short[i] - ma_long[i];
    }
    result["ssa_oscillatory"] = oscillatory;

    // Noise (residual)
    PriceVec noise(n);
    for (size_t i = 0; i < n; ++i) {
        noise[i] = detrended[i] - oscillatory[i];
    }
    result["ssa_noise"] = noise;

    // Signal-to-noise ratio
    auto trend_std = rolling_std(trend, 60);
    auto noise_std = rolling_std(noise, 60);
    PriceVec snr(n);
    for (size_t i = 0; i < n; ++i) {
        snr[i] = (noise_std[i] > 1e-9) ? trend_std[i] / noise_std[i] : 0.0;
    }
    result["ssa_snr"] = snr;

    return result;
}

// Feature #70: Fractional differentiation (preserves memory, removes unit root)
FeatureMap compute_fractional_diff_features(const PriceVec& prices, double d) {
    FeatureMap result;
    if (prices.size() < 100) return result;

    size_t n = prices.size();

    // Fractional differencing: (1-L)^d = Σ_k binom(d, k) * (-L)^k
    // Compute binomial coefficients
    int max_lag = 100;  // Truncate series
    std::vector<double> weights(max_lag);
    weights[0] = 1.0;
    for (int k = 1; k < max_lag; ++k) {
        weights[k] = weights[k-1] * (d - k + 1) / k * (-1);
    }

    // Apply weights
    PriceVec frac_diff(n, std::nan(""));
    for (int i = max_lag; i < static_cast<int>(n); ++i) {
        double sum = 0.0;
        for (int k = 0; k < max_lag; ++k) {
            sum += weights[k] * prices[i - k];
        }
        frac_diff[i] = sum;
    }

    result["frac_diff_" + std::to_string(static_cast<int>(d * 100))] = frac_diff;

    // Fractional diff returns
    auto fd_returns = pct_change(frac_diff, 1);
    result["frac_diff_returns_" + std::to_string(static_cast<int>(d * 100))] = fd_returns;

    return result;
}

} // namespace dominion::features
