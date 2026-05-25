#include "dominion/noise.hpp"
#ifdef DOMINION_HAS_FFTW3
#include <fftw3.h>
#endif
#include <cmath>
#include <algorithm>

namespace dominion::noise {

#ifdef DOMINION_HAS_FFTW3

VMDResult compute_vmd(const PriceVec& prices, int n_modes, double alpha) {
    VMDResult result;
    const int N = prices.size();

    // Initialize modes with random Gaussian noise
    result.modes.resize(n_modes);
    for (int k = 0; k < n_modes; ++k) {
        result.modes[k].resize(N);
        for (int i = 0; i < N; ++i) {
            result.modes[k][i] = prices[i] / n_modes + (rand() % 100 - 50) * 0.01;
        }
    }

    // Initialize center frequencies uniformly
    result.center_frequencies.resize(n_modes);
    for (int k = 0; k < n_modes; ++k) {
        result.center_frequencies[k] = static_cast<double>(k + 1) / (2.0 * n_modes);
    }

    // FFT buffers
    fftw_complex *fft_in = fftw_alloc_complex(N);
    fftw_complex *fft_out = fftw_alloc_complex(N);
    fftw_plan forward_plan = fftw_plan_dft_1d(N, fft_in, fft_out, FFTW_FORWARD, FFTW_ESTIMATE);
    fftw_plan inverse_plan = fftw_plan_dft_1d(N, fft_out, fft_in, FFTW_BACKWARD, FFTW_ESTIMATE);

    // Alternating Direction Method of Multipliers (ADMM) iterations
    const int max_iter = 500;
    const double tau = 0.0;
    const double tolerance = 1e-7;

    std::vector<std::vector<std::complex<double>>> u_hat(n_modes, std::vector<std::complex<double>>(N));
    std::vector<std::complex<double>> lambda_hat(N, 0.0);

    for (int iter = 0; iter < max_iter; ++iter) {
        // Update modes in frequency domain
        for (int k = 0; k < n_modes; ++k) {
            // Compute f_hat - sum(u_hat) + lambda_hat
            for (int i = 0; i < N; ++i) {
                fft_in[i][0] = prices[i];
                fft_in[i][1] = 0.0;
            }
            fftw_execute(forward_plan);

            std::vector<std::complex<double>> f_hat(N);
            for (int i = 0; i < N; ++i) {
                f_hat[i] = std::complex<double>(fft_out[i][0], fft_out[i][1]) / static_cast<double>(N);
            }

            for (int i = 0; i < N; ++i) {
                std::complex<double> sum_modes = 0.0;
                for (int j = 0; j < n_modes; ++j) {
                    if (j != k) {
                        sum_modes += u_hat[j][i];
                    }
                }

                double omega = static_cast<double>(i) / N;
                double omega_k = result.center_frequencies[k];
                double denominator = 1.0 + 2.0 * alpha * (omega - omega_k) * (omega - omega_k);

                u_hat[k][i] = (f_hat[i] - sum_modes + lambda_hat[i]) / denominator;
            }
        }

        // Update center frequencies
        for (int k = 0; k < n_modes; ++k) {
            double numerator = 0.0;
            double denominator = 0.0;

            for (int i = 0; i < N; ++i) {
                double omega = static_cast<double>(i) / N;
                double power = std::norm(u_hat[k][i]);
                numerator += omega * power;
                denominator += power;
            }

            if (denominator > 1e-12) {
                result.center_frequencies[k] = numerator / denominator;
            }
        }

        // Update Lagrange multipliers
        for (int i = 0; i < N; ++i) {
            // f_hat computation
            for (int j = 0; j < N; ++j) {
                fft_in[j][0] = (j == i) ? prices[j] : 0.0;
                fft_in[j][1] = 0.0;
            }

            std::complex<double> f_hat_i(prices[i], 0.0);
            std::complex<double> sum_modes = 0.0;
            for (int k = 0; k < n_modes; ++k) {
                sum_modes += u_hat[k][i];
            }

            lambda_hat[i] += tau * (f_hat_i - sum_modes);
        }

        // Check convergence (simplified)
        if (iter % 50 == 0) {
            double residual = 0.0;
            for (int i = 0; i < N; ++i) {
                std::complex<double> diff = 0.0;
                for (int k = 0; k < n_modes; ++k) {
                    diff += u_hat[k][i];
                }
                residual += std::norm(diff - std::complex<double>(prices[i], 0.0));
            }

            if (residual < tolerance) {
                break;
            }
        }
    }

    // Inverse FFT to get time-domain modes
    for (int k = 0; k < n_modes; ++k) {
        for (int i = 0; i < N; ++i) {
            fft_in[i][0] = u_hat[k][i].real();
            fft_in[i][1] = u_hat[k][i].imag();
        }
        fftw_execute(inverse_plan);

        for (int i = 0; i < N; ++i) {
            result.modes[k][i] = fft_out[i][0] / N;
        }
    }

    // Reconstruct signal
    result.reconstructed.resize(N, 0.0);
    for (int k = 0; k < n_modes; ++k) {
        for (int i = 0; i < N; ++i) {
            result.reconstructed[i] += result.modes[k][i];
        }
    }

    // Compute bandwidths (simplified - std dev of mode)
    result.bandwidths.resize(n_modes);
    for (int k = 0; k < n_modes; ++k) {
        double mean = 0.0;
        for (double val : result.modes[k]) {
            mean += val;
        }
        mean /= N;

        double variance = 0.0;
        for (double val : result.modes[k]) {
            variance += (val - mean) * (val - mean);
        }
        result.bandwidths[k] = std::sqrt(variance / N);
    }

    // Cleanup
    fftw_destroy_plan(forward_plan);
    fftw_destroy_plan(inverse_plan);
    fftw_free(fft_in);
    fftw_free(fft_out);

    return result;
}

#else

// Fallback without FFTW3
VMDResult compute_vmd(const PriceVec& prices, int n_modes, double alpha) {
    VMDResult result;
    // Stub: return empty result
    return result;
}

#endif

} // namespace dominion::noise
