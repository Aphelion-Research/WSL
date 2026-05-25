#include "dominion/multifractal.hpp"
#include <Eigen/Dense>
#include <cmath>

namespace dominion::multifractal {

PriceVec compute_dfa(const PriceVec& prices, int window) {
    const int N = prices.size();
    PriceVec dfa(N, std::nan(""));

    for (int idx = window; idx < N; ++idx) {
        double mean = 0.0;
        for (int i = idx - window; i < idx; ++i) {
            mean += prices[i];
        }
        mean /= window;

        PriceVec cumsum(window);
        cumsum[0] = prices[idx - window] - mean;
        for (int i = 1; i < window; ++i) {
            cumsum[i] = cumsum[i-1] + (prices[idx - window + i] - mean);
        }

        int box_size = window / 4;
        int num_boxes = window / box_size;
        double F = 0.0;

        for (int b = 0; b < num_boxes; ++b) {
            Eigen::VectorXd x(box_size), y(box_size);
            for (int i = 0; i < box_size; ++i) {
                x(i) = i;
                y(i) = cumsum[b * box_size + i];
            }

            Eigen::VectorXd coeffs = x.bdcSvd(Eigen::ComputeThinU | Eigen::ComputeThinV).solve(y);
            double var = 0.0;
            for (int i = 0; i < box_size; ++i) {
                double fitted = coeffs(0) * i + coeffs(1);
                var += (y(i) - fitted) * (y(i) - fitted);
            }
            F += var / box_size;
        }

        dfa[idx] = std::sqrt(F / num_boxes);
    }

    return dfa;
}

PriceVec compute_fractal_dimension(const PriceVec& prices, int window) {
    PriceVec hurst = compute_hurst_rs(prices, window);
    const int N = hurst.size();
    PriceVec fd(N);

    for (int i = 0; i < N; ++i) {
        fd[i] = 2.0 - hurst[i];
    }

    return fd;
}

PriceVec compute_holder_exponent(const PriceVec& prices, int window) {
    const int N = prices.size();
    PriceVec holder(N, std::nan(""));

    for (int idx = window; idx < N; ++idx) {
        std::vector<double> increments;
        for (int i = idx - window + 1; i < idx; ++i) {
            increments.push_back(std::abs(prices[i] - prices[i-1]));
        }

        double mean_inc = 0.0;
        for (double inc : increments) {
            mean_inc += inc;
        }
        mean_inc /= increments.size();

        double var_inc = 0.0;
        for (double inc : increments) {
            var_inc += (inc - mean_inc) * (inc - mean_inc);
        }
        var_inc /= increments.size();

        holder[idx] = 0.5 * std::log(var_inc) / std::log(static_cast<double>(window));
    }

    return holder;
}

PriceVec compute_singularity_width(const PriceVec& prices, int window) {
    const int N = prices.size();
    PriceVec width(N, std::nan(""));

    std::vector<double> q_orders = {-5, -3, -1, 0, 1, 3, 5};
    std::vector<int> scales = {4, 8, 16, 32, 64};

    for (int idx = window; idx < N; ++idx) {
        PriceVec segment(prices.begin() + idx - window, prices.begin() + idx);
        auto mfdfa_result = compute_mfdfa(segment, q_orders, scales);
        width[idx] = mfdfa_result.multifractal_width;
    }

    return width;
}

} // namespace dominion::multifractal
