#pragma once

#include "dominion/types.hpp"

#ifdef DOMINION_HAS_ITENSOR
#include <itensor/all.h>
#endif

namespace dominion::quantum {

// Tensor network decomposition
struct TensorDecomposition {
    int rank;
    double entanglement_entropy;
    PriceVec singular_values;
};

#ifdef DOMINION_HAS_ITENSOR
TensorDecomposition compute_tensor_decomposition(const PriceVec& prices, int window = 252);
#endif

// Entanglement entropy (measure of information spread)
PriceVec compute_entanglement_entropy(const PriceVec& prices, int window = 252);

} // namespace dominion::quantum
