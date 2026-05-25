#pragma once

#include "dominion/types.hpp"

#ifdef DOMINION_HAS_QUANTLIB
#include <ql/quantlib.hpp>
#endif

namespace dominion::stochastic_vol {

// Heston model calibration result
struct HestonParams {
    PriceVec kappa;       // Mean reversion speed
    PriceVec theta;       // Long-run volatility
    PriceVec sigma;       // Vol-of-vol
    PriceVec rho;         // Correlation
    PriceVec v0;          // Initial variance
};

#ifdef DOMINION_HAS_QUANTLIB
HestonParams calibrate_heston_rolling(const PriceVec& prices, int window = 252);
#endif

// SABR model parameters
struct SABRParams {
    PriceVec alpha;  // Initial volatility
    PriceVec beta;   // CEV exponent
    PriceVec rho;    // Correlation
    PriceVec nu;     // Vol-of-vol
};

SABRParams calibrate_sabr_rolling(const PriceVec& prices, int window = 252);

// Rough volatility (fractional Brownian motion)
PriceVec compute_rough_vol_hurst(const PriceVec& prices, int window = 252);

} // namespace dominion::stochastic_vol
