#pragma once

#include "dominion/types.hpp"

namespace dominion::copulas {

// Gaussian copula tail dependence
PriceVec compute_gaussian_copula_tail(const PriceVec& x, const PriceVec& y, double quantile = 0.05, int window = 252);

// t-copula (heavy tails)
PriceVec compute_t_copula_tail(const PriceVec& x, const PriceVec& y, int dof = 5, double quantile = 0.05, int window = 252);

// Clayton copula (lower tail dependence)
PriceVec compute_clayton_tail_dependence(const PriceVec& x, const PriceVec& y, int window = 252);

// Gumbel copula (upper tail dependence)
PriceVec compute_gumbel_tail_dependence(const PriceVec& x, const PriceVec& y, int window = 252);

} // namespace dominion::copulas
