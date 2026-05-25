#pragma once

#include "dominion/types.hpp"
#include <vector>
#include <string>

namespace dominion::causal {

// Granger causality test (rolling)
struct GrangerResult {
    PriceVec f_statistic;
    PriceVec p_value;
    PriceVec causality_strength;
};

GrangerResult compute_granger_causality(const PriceVec& x, const PriceVec& y, int max_lag = 5, int window = 252);

// Convergent Cross Mapping (CCM)
PriceVec compute_ccm_causality(const PriceVec& x, const PriceVec& y, int embed_dim = 3, int tau = 1, int window = 252);

// PC algorithm (causal discovery)
struct CausalGraph {
    std::vector<std::string> nodes;
    std::vector<std::pair<int,int>> edges;  // Directed edges (from, to)
};

CausalGraph compute_pc_algorithm(const std::vector<PriceVec>& series, const std::vector<std::string>& names, double alpha = 0.05);

} // namespace dominion::causal
