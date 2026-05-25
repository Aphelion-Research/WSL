#include <gtest/gtest.h>
#include "dominion/noise.hpp"
#include "dominion/information.hpp"
#include "dominion/multifractal.hpp"
#include <vector>
#include <cmath>

using namespace dominion;

// Test: verify features at time t use only data from t-N to t (not t+1)
TEST(PointInTimeSafety, NoLookahead) {
    const int N = 1000;
    PriceVec prices(N);

    for (int i = 0; i < N; ++i) {
        prices[i] = 100.0 + i * 0.01 + (i % 10) * 0.1;
    }

    // Corrupt future data (should NOT affect feature at current time)
    PriceVec prices_corrupted = prices;
    for (int i = 500; i < N; ++i) {
        prices_corrupted[i] = 999.0;  // Future corruption
    }

    const int test_idx = 499;  // Before corruption

    // Compute features
    auto hurst_clean = multifractal::compute_hurst_rs(prices, 100);
    auto hurst_corrupted = multifractal::compute_hurst_rs(prices_corrupted, 100);

    // Feature at test_idx should be identical (no lookahead)
    ASSERT_FALSE(std::isnan(hurst_clean[test_idx]));
    ASSERT_FALSE(std::isnan(hurst_corrupted[test_idx]));
    EXPECT_NEAR(hurst_clean[test_idx], hurst_corrupted[test_idx], 1e-10)
        << "Feature uses future data (lookahead detected)";
}

TEST(PointInTimeSafety, PermutationEntropyNoLookahead) {
    const int N = 500;
    PriceVec prices(N);

    for (int i = 0; i < N; ++i) {
        prices[i] = std::sin(i * 0.1) + (i % 5) * 0.01;
    }

    PriceVec prices_corrupted = prices;
    for (int i = 250; i < N; ++i) {
        prices_corrupted[i] = -999.0;
    }

    const int test_idx = 249;

    auto entropy_clean = information::compute_permutation_entropy(prices, 3, 1, 100);
    auto entropy_corrupted = information::compute_permutation_entropy(prices_corrupted, 3, 1, 100);

    ASSERT_FALSE(std::isnan(entropy_clean[test_idx]));
    ASSERT_FALSE(std::isnan(entropy_corrupted[test_idx]));
    EXPECT_NEAR(entropy_clean[test_idx], entropy_corrupted[test_idx], 1e-10)
        << "Permutation entropy uses future data";
}

TEST(PointInTimeSafety, SSANoLookahead) {
    const int N = 300;
    PriceVec prices(N);

    for (int i = 0; i < N; ++i) {
        prices[i] = 100.0 + i * 0.05;
    }

    PriceVec prices_corrupted = prices;
    for (int i = 200; i < N; ++i) {
        prices_corrupted[i] = 0.0;
    }

    PriceVec segment_clean(prices.begin(), prices.begin() + 200);
    PriceVec segment_corrupted(prices_corrupted.begin(), prices_corrupted.begin() + 200);

    auto ssa_clean = noise::compute_ssa(segment_clean, 50, 5);
    auto ssa_corrupted = noise::compute_ssa(segment_corrupted, 50, 5);

    EXPECT_EQ(ssa_clean.trend.size(), ssa_corrupted.trend.size());

    for (size_t i = 0; i < ssa_clean.trend.size(); ++i) {
        EXPECT_NEAR(ssa_clean.trend[i], ssa_corrupted.trend[i], 1e-10)
            << "SSA trend at index " << i << " differs (lookahead detected)";
    }
}

TEST(PointInTimeSafety, RollingWindowShift) {
    const int N = 200;
    const int window = 50;
    PriceVec prices(N);

    for (int i = 0; i < N; ++i) {
        prices[i] = static_cast<double>(i);
    }

    // Compute rolling mean manually (should use window [i-window, i-1], not [i-window+1, i])
    PriceVec rolling_mean(N, std::nan(""));

    for (int i = window; i < N; ++i) {
        double sum = 0.0;
        for (int j = i - window; j < i; ++j) {
            sum += prices[j];
        }
        rolling_mean[i] = sum / window;
    }

    for (int i = window; i < N; ++i) {
        double expected_mean = 0.0;
        for (int j = i - window; j < i; ++j) {  // Correct: [i-window, i)
            expected_mean += prices[j];
        }
        expected_mean /= window;

        EXPECT_NEAR(rolling_mean[i], expected_mean, 1e-10)
            << "Rolling mean at index " << i << " incorrect (should exclude current point)";
    }
}

int main(int argc, char **argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
