#pragma once

#include "dominion/types.hpp"
#include <vector>

namespace dominion::multifractal {

// Multifractal DFA result
struct MFDFAResult {
    std::vector<double> q_orders;  // q values used
    std::vector<double> hurst_q;   // Generalized Hurst exponent H(q)
    std::vector<double> tau_q;     // Scaling exponent τ(q)
    std::vector<double> alpha;     // Hölder exponent α
    std::vector<double> f_alpha;   // Singularity spectrum f(α)
    double multifractal_width;     // Δα (width of singularity spectrum)
};

MFDFAResult compute_mfdfa(const PriceVec& prices, const std::vector<double>& q_orders, const std::vector<int>& scales);

// Simple Hurst exponent (R/S analysis)
PriceVec compute_hurst_rs(const PriceVec& prices, int window = 252);

// Detrended Fluctuation Analysis (DFA)
PriceVec compute_dfa(const PriceVec& prices, int window = 252);

// Fractal dimension (box counting)
PriceVec compute_fractal_dimension(const PriceVec& prices, int window = 252);

// Local Hölder exponent
PriceVec compute_holder_exponent(const PriceVec& prices, int window = 60);

// Singularity spectrum width (rolling)
PriceVec compute_singularity_width(const PriceVec& prices, int window = 252);

} // namespace dominion::multifractal
