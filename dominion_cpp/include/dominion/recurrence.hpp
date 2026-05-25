#pragma once

#include "dominion/types.hpp"

namespace dominion::recurrence {

// Recurrence quantification analysis result
struct RQAResult {
    PriceVec recurrence_rate;
    PriceVec determinism;
    PriceVec laminarity;
    PriceVec entropy;
};

RQAResult compute_rqa(const PriceVec& prices, double threshold = 0.1, int embed_dim = 3, int delay = 1, int window = 252);

// Cross-recurrence (between two series)
PriceVec compute_cross_recurrence(const PriceVec& x, const PriceVec& y, double threshold = 0.1, int window = 252);

} // namespace dominion::recurrence
