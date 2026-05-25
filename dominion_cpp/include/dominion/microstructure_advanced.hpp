#pragma once

#include "dominion/types.hpp"

namespace dominion::microstructure {

// Hansen-Lunde realized variance estimator
PriceVec compute_hansen_lunde_rv(const PriceVec& prices, int window = 60);

// Pre-averaging estimator
PriceVec compute_preavg_rv(const PriceVec& prices, int window = 60);

// Two-scales realized variance (TSRV)
PriceVec compute_tsrv(const PriceVec& prices, int fast_scale = 1, int slow_scale = 5, int window = 60);

// Efficient price estimate (Ait-Sahalia noise model)
PriceVec estimate_efficient_price(const PriceVec& prices, int window = 60);

// Microstructure noise variance
PriceVec compute_noise_variance(const PriceVec& prices, int window = 60);

// Signal-to-noise ratio
PriceVec compute_microstructure_snr(const PriceVec& prices, int window = 60);

} // namespace dominion::microstructure
