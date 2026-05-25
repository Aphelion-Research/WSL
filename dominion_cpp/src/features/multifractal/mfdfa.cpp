#include "dominion/multifractal.hpp"
#include <Eigen/Dense>
#include <cmath>
#include <algorithm>

namespace dominion::multifractal {

namespace {

double compute_fluctuation_q(const PriceVec& cumsum, int scale, double q, int order = 1) {
    const int N = cumsum.size();
    const int num_segments = N / scale;

    double Fq = 0.0;

    for (int v = 0; v < num_segments; ++v) {
        int start = v * scale;
        int end = start + scale;

        Eigen::VectorXd x(scale);
        Eigen::VectorXd y(scale);

        for (int i = 0; i < scale; ++i) {
            x(i) = i;
            y(i) = cumsum[start + i];
        }

        Eigen::VectorXd coeffs = x.bdcSvd(Eigen::ComputeThinU | Eigen::ComputeThinV).solve(y);

        double variance = 0.0;
        for (int i = 0; i < scale; ++i) {
            double fitted = coeffs(0) * i + coeffs(1);
            double residual = y(i) - fitted;
            variance += residual * residual;
        }
        variance /= scale;

        if (std::abs(q) < 1e-10) {
            Fq += std::log(variance + 1e-12);
        } else {
            Fq += std::pow(variance, q / 2.0);
        }
    }

    if (std::abs(q) < 1e-10) {
        return std::exp(Fq / (2.0 * num_segments));
    } else {
        return std::pow(Fq / num_segments, 1.0 / q);
    }
}

} // anonymous namespace

MFDFAResult compute_mfdfa(const PriceVec& prices, const std::vector<double>& q_orders, const std::vector<int>& scales) {
    MFDFAResult result;
    result.q_orders = q_orders;

    PriceVec cumsum(prices.size());
    double mean = 0.0;
    for (double p : prices) {
        mean += p;
    }
    mean /= prices.size();

    cumsum[0] = prices[0] - mean;
    for (size_t i = 1; i < prices.size(); ++i) {
        cumsum[i] = cumsum[i-1] + (prices[i] - mean);
    }

    std::vector<std::vector<double>> Fq_scales(q_orders.size());

    for (size_t qi = 0; qi < q_orders.size(); ++qi) {
        double q = q_orders[qi];

        for (int scale : scales) {
            if (scale >= 4 && scale < static_cast<int>(prices.size()) / 4) {
                double Fq = compute_fluctuation_q(cumsum, scale, q);
                Fq_scales[qi].push_back(std::log(Fq));
            }
        }
    }

    for (size_t qi = 0; qi < q_orders.size(); ++qi) {
        if (Fq_scales[qi].size() < 2) {
            result.hurst_q.push_back(std::nan(""));
            continue;
        }

        Eigen::VectorXd log_scales(Fq_scales[qi].size());
        Eigen::VectorXd log_Fq(Fq_scales[qi].size());

        for (size_t i = 0; i < Fq_scales[qi].size(); ++i) {
            log_scales(i) = std::log(scales[i]);
            log_Fq(i) = Fq_scales[qi][i];
        }

        Eigen::VectorXd coeffs = log_scales.bdcSvd(Eigen::ComputeThinU | Eigen::ComputeThinV).solve(log_Fq);
        result.hurst_q.push_back(coeffs(0));
    }

    for (size_t i = 0; i < result.hurst_q.size(); ++i) {
        result.tau_q.push_back(result.hurst_q[i] * q_orders[i] - 1.0);
    }

    for (size_t i = 1; i < result.tau_q.size(); ++i) {
        double dtau = result.tau_q[i] - result.tau_q[i-1];
        double dq = q_orders[i] - q_orders[i-1];
        result.alpha.push_back(dtau / dq);
    }

    for (size_t i = 0; i < result.alpha.size(); ++i) {
        double f = q_orders[i] * result.alpha[i] - result.tau_q[i];
        result.f_alpha.push_back(f);
    }

    if (!result.alpha.empty()) {
        double alpha_min = *std::min_element(result.alpha.begin(), result.alpha.end());
        double alpha_max = *std::max_element(result.alpha.begin(), result.alpha.end());
        result.multifractal_width = alpha_max - alpha_min;
    } else {
        result.multifractal_width = 0.0;
    }

    return result;
}

PriceVec compute_hurst_rs(const PriceVec& prices, int window) {
    const int N = prices.size();
    PriceVec hurst(N, std::nan(""));

    for (int idx = window; idx < N; ++idx) {
        double mean = 0.0;
        for (int i = idx - window; i < idx; ++i) {
            mean += prices[i];
        }
        mean /= window;

        PriceVec cumdev(window);
        cumdev[0] = prices[idx - window] - mean;
        for (int i = 1; i < window; ++i) {
            cumdev[i] = cumdev[i-1] + (prices[idx - window + i] - mean);
        }

        double R = *std::max_element(cumdev.begin(), cumdev.end()) -
                   *std::min_element(cumdev.begin(), cumdev.end());

        double S = 0.0;
        for (int i = idx - window; i < idx; ++i) {
            S += (prices[i] - mean) * (prices[i] - mean);
        }
        S = std::sqrt(S / window);

        if (S > 1e-12) {
            double RS = R / S;
            hurst[idx] = std::log(RS) / std::log(window);
        }
    }

    return hurst;
}

} // namespace dominion::multifractal
