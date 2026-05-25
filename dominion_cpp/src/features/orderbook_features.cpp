#include "dominion/features.hpp"
#include <cmath>
#include <algorithm>
#include <numeric>

namespace dominion::features {

// Feature #21: Kyle's lambda (price impact per unit volume)
// lambda = Δprice / sqrt(volume)
FeatureMap compute_kyles_lambda(const PriceVec& close, const PriceVec& volume, int window) {
    FeatureMap result;
    if (close.size() != volume.size() || close.size() < static_cast<size_t>(window)) {
        return result;
    }

    size_t n = close.size();
    PriceVec lambda(n, std::nan(""));

    for (int i = window; i < static_cast<int>(n); ++i) {
        double sum_price_impact = 0.0;
        double sum_volume = 0.0;
        int count = 0;

        for (int t = i - window + 1; t < i; ++t) {
            if (volume[t] > 0) {
                double price_change = std::abs(close[t] - close[t-1]);
                double sqrt_vol = std::sqrt(volume[t]);
                sum_price_impact += price_change;
                sum_volume += sqrt_vol;
                count++;
            }
        }

        lambda[i] = (count > 0 && sum_volume > 0) ? sum_price_impact / sum_volume : 0.0;
    }

    result["kyles_lambda_" + std::to_string(window)] = lambda;

    // Lambda z-score (high lambda = low liquidity)
    auto lambda_mean = rolling_mean(lambda, 60);
    auto lambda_std = rolling_std(lambda, 60);
    PriceVec lambda_z(n);
    for (size_t i = 0; i < n; ++i) {
        lambda_z[i] = (lambda_std[i] > 1e-9) ?
            (lambda[i] - lambda_mean[i]) / lambda_std[i] : 0.0;
    }
    result["kyles_lambda_zscore_" + std::to_string(window)] = lambda_z;

    return result;
}

// Feature #22: Roll's effective spread estimator
// spread = 2 * sqrt(-cov(Δp_t, Δp_{t-1}))
FeatureMap compute_roll_spread(const PriceVec& close, int window) {
    FeatureMap result;
    if (close.size() < static_cast<size_t>(window + 2)) return result;

    size_t n = close.size();
    PriceVec spread(n, std::nan(""));

    // Compute price changes
    auto price_changes = diff(close, 1);

    for (int i = window; i < static_cast<int>(n); ++i) {
        // Compute covariance of Δp_t and Δp_{t-1}
        double sum_xy = 0.0;
        double sum_x = 0.0;
        double sum_y = 0.0;
        int count = 0;

        for (int t = i - window + 1; t < i; ++t) {
            if (!std::isnan(price_changes[t]) && !std::isnan(price_changes[t-1])) {
                sum_x += price_changes[t];
                sum_y += price_changes[t-1];
                sum_xy += price_changes[t] * price_changes[t-1];
                count++;
            }
        }

        if (count > 0) {
            double mean_x = sum_x / count;
            double mean_y = sum_y / count;
            double cov = (sum_xy / count) - mean_x * mean_y;

            // Roll's formula: spread = 2 * sqrt(-cov)
            spread[i] = (cov < 0) ? 2.0 * std::sqrt(-cov) : 0.0;
        }
    }

    result["roll_spread_" + std::to_string(window)] = spread;

    // Spread relative to price
    PriceVec spread_bps(n);
    for (size_t i = 0; i < n; ++i) {
        spread_bps[i] = (close[i] > 0) ? (spread[i] / close[i]) * 10000 : 0.0;
    }
    result["roll_spread_bps_" + std::to_string(window)] = spread_bps;

    return result;
}

// Feature #23: Corwin-Schultz high-low spread estimator
// Uses high-low ratio over multiple periods
FeatureMap compute_corwin_schultz_spread(const PriceVec& high, const PriceVec& low) {
    FeatureMap result;
    if (high.size() != low.size() || high.size() < 3) return result;

    size_t n = high.size();
    PriceVec spread(n, std::nan(""));

    for (int i = 2; i < static_cast<int>(n); ++i) {
        // High-low ratio for single period
        double hl_ratio = (high[i] > 0 && low[i] > 0) ?
            std::log(high[i] / low[i]) : 0.0;

        // High-low ratio for two-period span
        double h2 = std::max(high[i], high[i-1]);
        double l2 = std::min(low[i], low[i-1]);
        double hl_ratio_2 = (h2 > 0 && l2 > 0) ? std::log(h2 / l2) : 0.0;

        // Corwin-Schultz estimator
        double alpha = (std::sqrt(2 * hl_ratio_2) - std::sqrt(hl_ratio)) /
                       (3 - 2 * std::sqrt(2));
        alpha = std::max(0.0, alpha);  // Non-negative

        spread[i] = 2 * (std::exp(alpha) - 1) / (1 + std::exp(alpha));
    }

    result["corwin_schultz_spread"] = spread;

    // Spread in basis points
    PriceVec spread_bps(n);
    for (size_t i = 0; i < n; ++i) {
        double mid = (high[i] + low[i]) / 2.0;
        spread_bps[i] = (mid > 0) ? (spread[i] / mid) * 10000 : 0.0;
    }
    result["corwin_schultz_spread_bps"] = spread_bps;

    return result;
}

// Feature #41: Order book imbalance proxy (volume-weighted price position within bar)
// Measures whether volume concentrated at bid or ask
FeatureMap compute_orderbook_imbalance_proxy(const PriceVec& open, const PriceVec& close,
                                             const PriceVec& high, const PriceVec& low,
                                             const PriceVec& volume) {
    FeatureMap result;
    if (open.size() != close.size()) return result;

    size_t n = open.size();
    PriceVec imbalance(n);

    for (size_t i = 0; i < n; ++i) {
        double range = high[i] - low[i];
        if (range > 1e-9) {
            // Close position within range: 1.0 = closed at high, 0.0 = closed at low
            double close_pos = (close[i] - low[i]) / range;

            // Weighted by volume
            imbalance[i] = (close_pos - 0.5) * volume[i];  // Positive = buying pressure
        } else {
            imbalance[i] = 0.0;
        }
    }

    result["orderbook_imbalance_proxy"] = imbalance;

    // Cumulative imbalance over rolling window
    for (int window : {10, 30, 60}) {
        PriceVec cum_imbalance(n, std::nan(""));
        for (int i = window; i < static_cast<int>(n); ++i) {
            double sum = 0.0;
            for (int t = i - window; t < i; ++t) {
                sum += imbalance[t];
            }
            cum_imbalance[i] = sum;
        }
        result["orderbook_cumulative_imbalance_" + std::to_string(window)] = cum_imbalance;
    }

    return result;
}

// Feature #44: Price impact asymmetry (up-moves vs down-moves)
FeatureMap compute_price_impact_asymmetry(const PriceVec& close, const PriceVec& volume, int window) {
    FeatureMap result;
    if (close.size() != volume.size()) return result;

    size_t n = close.size();
    auto returns = log_returns(close, 1);

    PriceVec up_impact(n, std::nan(""));
    PriceVec down_impact(n, std::nan(""));
    PriceVec asymmetry(n, std::nan(""));

    for (int i = window; i < static_cast<int>(n); ++i) {
        double sum_up_ret = 0.0, sum_down_ret = 0.0;
        double sum_up_vol = 0.0, sum_down_vol = 0.0;

        for (int t = i - window; t < i; ++t) {
            if (returns[t] > 0) {
                sum_up_ret += returns[t];
                sum_up_vol += volume[t];
            } else if (returns[t] < 0) {
                sum_down_ret += std::abs(returns[t]);
                sum_down_vol += volume[t];
            }
        }

        up_impact[i] = (sum_up_vol > 0) ? sum_up_ret / sum_up_vol : 0.0;
        down_impact[i] = (sum_down_vol > 0) ? sum_down_ret / sum_down_vol : 0.0;

        // Asymmetry: positive = easier to push price up than down
        asymmetry[i] = (up_impact[i] + down_impact[i] > 1e-9) ?
            (up_impact[i] - down_impact[i]) / (up_impact[i] + down_impact[i]) : 0.0;
    }

    result["price_impact_up_" + std::to_string(window)] = up_impact;
    result["price_impact_down_" + std::to_string(window)] = down_impact;
    result["price_impact_asymmetry_" + std::to_string(window)] = asymmetry;

    return result;
}

} // namespace dominion::features
