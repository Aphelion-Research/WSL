#pragma once

#include "dominion/types.hpp"

#include <string>
#include <unordered_map>
#include <vector>

namespace dominion {

// Rolling window computations — all point-in-time safe (shift by 1)
namespace features {

// Price features (~80)
FeatureMap compute_price_features(const PriceVec& close, const PriceVec& high,
                                  const PriceVec& low, const PriceVec& volume,
                                  const std::vector<int>& windows);

// Microstructure features (~60)
FeatureMap compute_microstructure_features(const PriceVec& close, const PriceVec& high,
                                           const PriceVec& low, const PriceVec& volume,
                                           const std::vector<int>& windows);

// Cross-asset features (~100)
FeatureMap compute_crossasset_features(const PriceVec& gold_returns,
                                       const std::unordered_map<std::string, PriceVec>& macro_series,
                                       const std::vector<int>& windows);

// COT features (~30)
FeatureMap compute_cot_features(const std::vector<COTData>& cot,
                                const std::vector<int>& windows);

// Macro features (~60)
FeatureMap compute_macro_features(const PriceVec& gold_close,
                                  const std::unordered_map<std::string, PriceVec>& macro_series,
                                  const std::vector<std::string>& fomc_dates);

// Regime features (~40)
FeatureMap compute_regime_features(const PriceVec& returns, const PriceVec& volatility,
                                   const PriceVec& volume,
                                   const std::vector<Timestamp>& timestamps);

// Calendar features (~30)
FeatureMap compute_calendar_features(const std::vector<Timestamp>& timestamps,
                                     const std::vector<std::string>& fomc_dates);

// ML-based features (~15)
FeatureMap compute_autoencoder_anomalies(const FeatureMap& input_features,
                                         const std::vector<std::string>& feature_names,
                                         int n_components = 10);

FeatureMap compute_feature_stability(const FeatureMap& features,
                                     const PriceVec& returns,
                                     int window = 60);

FeatureMap compute_data_quality_score(const std::vector<Bar>& bars);

// Signal processing features (~20)
FeatureMap compute_emd_features(const PriceVec& prices);
FeatureMap compute_hilbert_features(const PriceVec& prices);
FeatureMap compute_ssa_features(const PriceVec& prices, int window_length = 60, int n_components = 3);
FeatureMap compute_fractional_diff_features(const PriceVec& prices, double d = 0.5);

// Order book / microstructure advanced (~15)
FeatureMap compute_kyles_lambda(const PriceVec& close, const PriceVec& volume, int window = 60);
FeatureMap compute_roll_spread(const PriceVec& close, int window = 60);
FeatureMap compute_corwin_schultz_spread(const PriceVec& high, const PriceVec& low);
FeatureMap compute_orderbook_imbalance_proxy(const PriceVec& open, const PriceVec& close,
                                             const PriceVec& high, const PriceVec& low,
                                             const PriceVec& volume);
FeatureMap compute_price_impact_asymmetry(const PriceVec& close, const PriceVec& volume, int window = 60);

// Cross-asset advanced (~20)
FeatureMap compute_dcc_correlations(const PriceVec& gold_returns,
                                    const std::unordered_map<std::string, PriceVec>& macro_returns,
                                    double lambda = 0.94);
FeatureMap compute_copula_tail_dependence(const PriceVec& gold_returns,
                                          const std::unordered_map<std::string, PriceVec>& macro_returns,
                                          double tail_quantile = 0.05,
                                          int window = 252);
FeatureMap compute_pca_regime_features(const std::unordered_map<std::string, PriceVec>& macro_returns,
                                       int window = 252);
FeatureMap compute_network_centrality(const PriceVec& gold_returns,
                                      const std::unordered_map<std::string, PriceVec>& macro_returns,
                                      double corr_threshold = 0.5,
                                      int window = 252);

// Causal inference features (~15)
FeatureMap compute_transfer_entropy(const PriceVec& source_series,
                                    const PriceVec& target_series,
                                    int n_bins = 10,
                                    int lag = 1,
                                    int window = 252);
FeatureMap compute_ccm_causality(const PriceVec& x_series,
                                 const PriceVec& y_series,
                                 int embed_dim = 3,
                                 int tau = 1,
                                 int window = 252);
FeatureMap compute_causal_dag_strengths(const PriceVec& gold_returns,
                                        const std::unordered_map<std::string, PriceVec>& macro_returns,
                                        int lag = 1,
                                        int window = 252);
FeatureMap compute_granger_causality_rolling(const PriceVec& x_series,
                                            const PriceVec& y_series,
                                            int max_lag = 5,
                                            int window = 252);

} // namespace features

// Feature validation
void validate_features(FeatureMap& features, double clip_sigma = 100.0);

// IC computation
std::unordered_map<std::string, double> compute_ic(
    const FeatureMap& features, const PriceVec& forward_returns, int window = 252);

// Rolling statistics primitives
PriceVec rolling_mean(const PriceVec& data, int window);
PriceVec rolling_std(const PriceVec& data, int window);
PriceVec rolling_skew(const PriceVec& data, int window);
PriceVec rolling_kurtosis(const PriceVec& data, int window);
PriceVec rolling_correlation(const PriceVec& x, const PriceVec& y, int window);
PriceVec ema(const PriceVec& data, int period);
PriceVec diff(const PriceVec& data, int lag = 1);
PriceVec pct_change(const PriceVec& data, int lag = 1);
PriceVec log_returns(const PriceVec& data, int lag = 1);
PriceVec cummax(const PriceVec& data);
PriceVec drawdown(const PriceVec& data);

} // namespace dominion
