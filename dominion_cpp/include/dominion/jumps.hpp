#pragma once

#include "dominion/types.hpp"

namespace dominion::jumps {

// Lee-Mykland jump test
struct JumpResult {
    PriceVec jump_detected;  // Binary: 1 = jump, 0 = no jump
    PriceVec jump_size;
    PriceVec test_statistic;
};

JumpResult compute_lee_mykland_jumps(const PriceVec& prices, int window = 252, double threshold = 4.6);

// Barndorff-Nielsen-Shephard (BNS) jump-robust variance
PriceVec compute_bns_variance(const PriceVec& prices, int window = 60);

// Bipower variation
PriceVec compute_bipower_variation(const PriceVec& prices, int window = 60);

// Hawkes process intensity estimation
PriceVec compute_hawkes_intensity(const std::vector<double>& jump_times, double alpha, double beta, int window);

} // namespace dominion::jumps
