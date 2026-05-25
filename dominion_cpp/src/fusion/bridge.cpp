#include "dominion/fusion.hpp"
#include <random>
#include <algorithm>
#include <cmath>

namespace dominion {

std::vector<SyntheticTick> brownian_bridge(
    double open, double high, double low, double close,
    Timestamp start, Timestamp end,
    int n_ticks, double sigma
) {
    std::vector<SyntheticTick> ticks;
    ticks.reserve(n_ticks + 4);  // +4 for open/high/low/close

    std::mt19937 rng(std::random_device{}());
    std::normal_distribution<double> normal(0.0, 1.0);

    auto start_ms = std::chrono::duration_cast<std::chrono::milliseconds>(start.time_since_epoch()).count();
    auto end_ms = std::chrono::duration_cast<std::chrono::milliseconds>(end.time_since_epoch()).count();
    double duration_ms = static_cast<double>(end_ms - start_ms);

    // Generate Brownian bridge path
    std::vector<double> prices;
    std::vector<double> times;
    prices.reserve(n_ticks);
    times.reserve(n_ticks);

    for (int i = 0; i < n_ticks; ++i) {
        double t = static_cast<double>(i) / (n_ticks - 1);  // [0, 1]
        times.push_back(t);

        // Brownian bridge: W(t) = open + (close - open) * t + sqrt(t*(1-t)) * sigma * Z
        double drift = open + (close - open) * t;
        double stochastic = std::sqrt(t * (1.0 - t)) * sigma * normal(rng);
        prices.push_back(drift + stochastic);
    }

    // Force high/low to appear in path
    int high_idx = n_ticks / 3;  // first third
    int low_idx = 2 * n_ticks / 3;  // second third
    if (high < low) std::swap(high_idx, low_idx);  // swap if inverted

    prices[high_idx] = high;
    prices[low_idx] = low;

    // Smooth transitions around extrema
    for (int i = std::max(0, high_idx - 2); i < std::min(n_ticks, high_idx + 3); ++i) {
        if (i != high_idx) {
            prices[i] = 0.5 * (prices[i] + high);
        }
    }
    for (int i = std::max(0, low_idx - 2); i < std::min(n_ticks, low_idx + 3); ++i) {
        if (i != low_idx) {
            prices[i] = 0.5 * (prices[i] + low);
        }
    }

    // Convert to ticks with timestamps
    for (size_t i = 0; i < prices.size(); ++i) {
        int64_t tick_ms = start_ms + static_cast<int64_t>(times[i] * duration_ms);
        Timestamp ts = Timestamp(std::chrono::milliseconds(tick_ms));

        double confidence = 0.5;  // default for synthetic
        if (i == 0 || i == n_ticks - 1) confidence = 1.0;  // open/close exact
        if (i == static_cast<size_t>(high_idx) || i == static_cast<size_t>(low_idx)) {
            confidence = 1.0;  // high/low exact
        }

        ticks.push_back({ts, prices[i], confidence});
    }

    return ticks;
}

} // namespace dominion
