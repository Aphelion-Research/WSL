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
