#include "dominion/microstructure_advanced.hpp"
#include <cmath>

namespace dominion::microstructure {

PriceVec compute_hansen_lunde_rv(const PriceVec& prices, int window) {
    const int N = prices.size();
    PriceVec rv(N, std::nan(""));

    for (int idx = window; idx < N; ++idx) {
        double sum_sq = 0.0;
        for (int i = idx - window + 1; i < idx; ++i) {
            double ret = prices[i] - prices[i-1];
            sum_sq += ret * ret;
        }

        double gamma1 = 0.0;
        for (int i = idx - window + 2; i < idx; ++i) {
            double ret1 = prices[i] - prices[i-1];
            double ret2 = prices[i-1] - prices[i-2];
            gamma1 += ret1 * ret2;
        }
        gamma1 /= (window - 2);

        rv[idx] = sum_sq / window + 2.0 * gamma1;
    }

    return rv;
}

PriceVec compute_preavg_rv(const PriceVec& prices, int window) {
    const int N = prices.size();
    PriceVec rv(N, std::nan(""));
    const int theta = std::max(2, static_cast<int>(std::sqrt(window)));

    for (int idx = window; idx < N; ++idx) {
        PriceVec preavg(window - theta + 1);
        for (int i = 0; i < static_cast<int>(preavg.size()); ++i) {
            double sum = 0.0;
            for (int j = 0; j < theta; ++j) {
                sum += prices[idx - window + i + j];
            }
            preavg[i] = sum / theta;
        }

        double sum_sq = 0.0;
        for (size_t i = 1; i < preavg.size(); ++i) {
            double diff = preavg[i] - preavg[i-1];
            sum_sq += diff * diff;
        }

        rv[idx] = sum_sq / (preavg.size() - 1);
    }

    return rv;
}

PriceVec compute_tsrv(const PriceVec& prices, int fast_scale, int slow_scale, int window) {
    const int N = prices.size();
    PriceVec tsrv(N, std::nan(""));

    for (int idx = window; idx < N; ++idx) {
        double rv_fast = 0.0, rv_slow = 0.0;

        for (int i = idx - window + fast_scale; i < idx; i += fast_scale) {
            double ret = prices[i] - prices[i - fast_scale];
            rv_fast += ret * ret;
        }
        rv_fast /= (window / fast_scale);

        for (int i = idx - window + slow_scale; i < idx; i += slow_scale) {
            double ret = prices[i] - prices[i - slow_scale];
            rv_slow += ret * ret;
        }
        rv_slow /= (window / slow_scale);

        double c = static_cast<double>(slow_scale) / fast_scale;
        tsrv[idx] = rv_slow - (1.0 / c) * rv_fast;
    }

    return tsrv;
}

PriceVec estimate_efficient_price(const PriceVec& prices, int window) {
    const int N = prices.size();
    PriceVec efficient(N, std::nan(""));

    for (int idx = window; idx < N; ++idx) {
        double sum = 0.0;
        for (int i = idx - window; i < idx; ++i) {
            sum += prices[i];
        }
        efficient[idx] = sum / window;
    }

    return efficient;
}

PriceVec compute_noise_variance(const PriceVec& prices, int window) {
    const int N = prices.size();
    PriceVec noise_var(N, std::nan(""));

    for (int idx = window; idx < N; ++idx) {
        double gamma0 = 0.0;
        for (int i = idx - window + 1; i < idx; ++i) {
            double ret = prices[i] - prices[i-1];
            gamma0 += ret * ret;
        }
        gamma0 /= (window - 1);

        double gamma1 = 0.0;
        for (int i = idx - window + 2; i < idx; ++i) {
            double ret1 = prices[i] - prices[i-1];
            double ret2 = prices[i-1] - prices[i-2];
            gamma1 += ret1 * ret2;
        }
        gamma1 /= (window - 2);

        noise_var[idx] = -gamma1;
    }

    return noise_var;
}

PriceVec compute_microstructure_snr(const PriceVec& prices, int window) {
    PriceVec rv = compute_hansen_lunde_rv(prices, window);
    PriceVec noise_var = compute_noise_variance(prices, window);

    const int N = prices.size();
    PriceVec snr(N);

    for (int i = 0; i < N; ++i) {
        double signal_var = std::max(0.0, rv[i] - 2.0 * noise_var[i]);
        snr[i] = signal_var / (noise_var[i] + 1e-12);
    }

    return snr;
}

} // namespace dominion::microstructure
