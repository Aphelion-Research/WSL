#pragma once

#include "dominion/types.hpp"
#include <vector>
#include <complex>

namespace dominion::noise {

// Singular Spectrum Analysis (SSA)
struct SSAResult {
    std::vector<PriceVec> components;  // Decomposed components
    std::vector<double> singular_values;
    std::vector<double> explained_variance;
    PriceVec trend;
    PriceVec noise;
};

SSAResult compute_ssa(const PriceVec& prices, int window_length, int n_components);

// Empirical Mode Decomposition (EMD)
struct EMDResult {
    std::vector<PriceVec> imfs;  // Intrinsic Mode Functions
    PriceVec residual;
    std::vector<double> frequencies;  // Dominant frequency per IMF
    std::vector<double> energies;     // Energy per IMF
};

EMDResult compute_emd(const PriceVec& prices, int max_imfs = 10);

// Variational Mode Decomposition (VMD)
struct VMDResult {
    std::vector<PriceVec> modes;
    std::vector<double> center_frequencies;
    std::vector<double> bandwidths;
    PriceVec reconstructed;
};

VMDResult compute_vmd(const PriceVec& prices, int n_modes, double alpha = 2000.0);

// Wavelet Packet Decomposition
struct WaveletResult {
    std::vector<PriceVec> details;  // Detail coefficients at each level
    std::vector<PriceVec> approx;   // Approximation coefficients
    std::vector<double> energies;   // Energy per level
};

WaveletResult compute_wavelet_packet(const PriceVec& prices, int levels, const std::string& wavelet = "db4");

// Feature extraction from decompositions
FeatureMap extract_noise_features(const SSAResult& ssa, const EMDResult& emd, const VMDResult& vmd);

// Mode crossing detection (when decomposed modes flip dominance)
PriceVec detect_mode_crossings(const std::vector<PriceVec>& modes, int window = 20);

// Signal-to-noise ratio
PriceVec compute_snr(const PriceVec& signal, const PriceVec& noise, int window = 60);

// Adaptive noise filter (Wiener-like)
PriceVec adaptive_denoise(const PriceVec& prices, int window = 60);

} // namespace dominion::noise
