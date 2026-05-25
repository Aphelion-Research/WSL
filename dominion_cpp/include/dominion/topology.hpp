#pragma once

#include "dominion/types.hpp"
#include <vector>

#ifdef DOMINION_HAS_GUDHI
#include <gudhi/Simplex_tree.h>
#include <gudhi/Persistent_cohomology.h>
#endif

namespace dominion::topology {

// Persistent homology result
struct PersistenceResult {
    std::vector<double> birth_times;
    std::vector<double> death_times;
    std::vector<int> dimensions;  // 0=components, 1=loops, 2=voids
    std::vector<double> lifetimes;
};

#ifdef DOMINION_HAS_GUDHI
PersistenceResult compute_persistent_homology(const PriceVec& prices, int embed_dim = 3, int delay = 1);
#endif

// Takens embedding (phase space reconstruction)
std::vector<std::vector<double>> takens_embedding(const PriceVec& prices, int embed_dim, int delay);

// Betti numbers (topological features)
struct BettiNumbers {
    PriceVec betti_0;  // Connected components
    PriceVec betti_1;  // Loops
    PriceVec betti_2;  // Voids
};

BettiNumbers compute_betti_rolling(const PriceVec& prices, int window = 252);

} // namespace dominion::topology
