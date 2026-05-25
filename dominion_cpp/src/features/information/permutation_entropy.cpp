#include "dominion/information.hpp"
#include <cmath>
#include <map>
#include <vector>
#include <algorithm>

namespace dominion::information {

namespace {

// Encode ordinal pattern (permutation)
std::vector<int> ordinal_pattern(const PriceVec& values, int start, int embed_dim, int delay) {
    std::vector<int> indices(embed_dim);
    for (int i = 0; i < embed_dim; ++i) {
        indices[i] = i;
    }

    // Sort indices by corresponding values
    std::sort(indices.begin(), indices.end(), [&](int a, int b) {
        return values[start + a * delay] < values[start + b * delay];
    });

    return indices;
}

// Convert ordinal pattern to unique ID
int pattern_to_id(const std::vector<int>& pattern) {
    int id = 0;
    int factorial = 1;
    for (size_t i = 0; i < pattern.size(); ++i) {
        int smaller_count = 0;
        for (size_t j = i + 1; j < pattern.size(); ++j) {
            if (pattern[j] < pattern[i]) {
                smaller_count++;
            }
        }
        id += smaller_count * factorial;
        factorial *= (i + 1);
    }
    return id;
}

} // anonymous namespace

PriceVec compute_permutation_entropy(const PriceVec& prices, int embed_dim, int delay, int window) {
    const int N = prices.size();
    PriceVec entropy(N, std::nan(""));

    const int pattern_length = (embed_dim - 1) * delay + 1;

    for (int i = window; i < N; ++i) {
        std::map<int, int> pattern_counts;
        int total_patterns = 0;

        // Count patterns in window
        for (int j = i - window; j < i - pattern_length + 1 && j >= 0; ++j) {
            auto pattern = ordinal_pattern(prices, j, embed_dim, delay);
            int pattern_id = pattern_to_id(pattern);
            pattern_counts[pattern_id]++;
            total_patterns++;
        }

        // Compute entropy
        double H = 0.0;
        for (const auto& [pattern_id, count] : pattern_counts) {
            double p = static_cast<double>(count) / total_patterns;
            if (p > 0.0) {
                H -= p * std::log2(p);
            }
        }

        // Normalize by maximum possible entropy
        int n_possible_patterns = 1;
        for (int k = 1; k <= embed_dim; ++k) {
            n_possible_patterns *= k;
        }
        double H_max = std::log2(n_possible_patterns);

        entropy[i] = H / (H_max + 1e-12);
    }

    return entropy;
}

} // namespace dominion::information
