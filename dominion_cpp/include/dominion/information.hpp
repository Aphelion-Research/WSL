#pragma once

#include "dominion/types.hpp"
#include <vector>

namespace dominion::information {

// Permutation entropy (order pattern complexity)
PriceVec compute_permutation_entropy(const PriceVec& prices, int embed_dim = 3, int delay = 1, int window = 100);

// Sample entropy (irregularity measure)
PriceVec compute_sample_entropy(const PriceVec& prices, int m = 2, double r = 0.2, int window = 100);

// Approximate entropy
PriceVec compute_approximate_entropy(const PriceVec& prices, int m = 2, double r = 0.2, int window = 100);

// Transfer entropy (X→Y information flow)
PriceVec compute_transfer_entropy(const PriceVec& source, const PriceVec& target, int n_bins = 10, int lag = 1, int window = 252);

// Mutual information
PriceVec compute_mutual_information(const PriceVec& x, const PriceVec& y, int n_bins = 10, int window = 252);

// Lempel-Ziv complexity
PriceVec compute_lz_complexity(const PriceVec& prices, int window = 100);

// Complexity-entropy plane coordinates
struct ComplexityEntropyPoint {
    double complexity;
    double entropy;
};

std::vector<ComplexityEntropyPoint> compute_complexity_entropy_plane(const PriceVec& prices, int embed_dim = 3, int window = 100);

// Conditional entropy H(Y|X)
PriceVec compute_conditional_entropy(const PriceVec& x, const PriceVec& y, int n_bins = 10, int window = 252);

// Joint entropy H(X,Y)
PriceVec compute_joint_entropy(const PriceVec& x, const PriceVec& y, int n_bins = 10, int window = 252);

// Kullback-Leibler divergence (rolling)
PriceVec compute_kl_divergence(const PriceVec& p_series, const PriceVec& q_series, int n_bins = 10, int window = 252);

} // namespace dominion::information
