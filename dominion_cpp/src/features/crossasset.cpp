#include <cmath>
#include "dominion/features.hpp"
#include <algorithm>

namespace dominion::features {

FeatureMap compute_crossasset_features(const PriceVec& gold_returns,
                                       const std::unordered_map<std::string, PriceVec>& macro_series,
                                       const std::vector<int>& windows) {
    FeatureMap features;
    
    // Key series for cross-asset analysis
    std::vector<std::string> key_series = {
        "DGS10", "DGS2", "DTWEXBGS", "VIXCLS", "CPIAUCSL", 
        "FEDFUNDS", "T10Y2Y", "T5YIFR", "DFII10"
    };
    
    for (const auto& series_id : key_series) {
        if (macro_series.find(series_id) == macro_series.end()) continue;
        
        const auto& series_data = macro_series.at(series_id);
        
        // Compute returns for the series
        PriceVec series_returns = pct_change(series_data, 1);
        
        // Ensure same length
        size_t n = std::min(gold_returns.size(), series_returns.size());
        
        // Rolling correlation at multiple windows
        for (int w : windows) {
            if (n < static_cast<size_t>(w)) continue;
            
            PriceVec corr(n, std::nan(""));
            
            for (size_t i = w; i < n; ++i) {
                double sum_x = 0.0, sum_y = 0.0, sum_xy = 0.0, sum_xx = 0.0, sum_yy = 0.0;
                int count = 0;
                
                for (int j = 0; j < w; ++j) {
                    size_t idx = i - j;
                    double x = gold_returns[idx];
                    double y = series_returns[idx];
                    
                    if (std::isnan(x) || std::isnan(y)) continue;
                    
                    sum_x += x;
                    sum_y += y;
                    sum_xy += x * y;
                    sum_xx += x * x;
                    sum_yy += y * y;
                    ++count;
                }
                
                if (count < w / 2) continue;  // Require at least half valid samples
                
                double mean_x = sum_x / count;
                double mean_y = sum_y / count;
                double cov = (sum_xy / count) - mean_x * mean_y;
                double std_x = std::sqrt((sum_xx / count) - mean_x * mean_x);
                double std_y = std::sqrt((sum_yy / count) - mean_y * mean_y);
                
                if (std_x > 1e-9 && std_y > 1e-9) {
                    corr[i] = cov / (std_x * std_y);
                }
            }
            
            features["corr_" + series_id + "_" + std::to_string(w)] = corr;
        }
        
        // Rolling beta (gold vs series)
        for (int w : windows) {
            if (n < static_cast<size_t>(w)) continue;
            
            PriceVec beta(n, std::nan(""));
            
            for (size_t i = w; i < n; ++i) {
                double sum_xy = 0.0, sum_xx = 0.0;
                int count = 0;
                
                for (int j = 0; j < w; ++j) {
                    size_t idx = i - j;
                    double x = series_returns[idx];
                    double y = gold_returns[idx];
                    
                    if (std::isnan(x) || std::isnan(y)) continue;
                    
                    sum_xy += x * y;
                    sum_xx += x * x;
                    ++count;
                }
                
                if (count < w / 2 || sum_xx < 1e-9) continue;
                
                beta[i] = sum_xy / sum_xx;
            }
            
            features["beta_" + series_id + "_" + std::to_string(w)] = beta;
        }
        
        // Lead-lag correlation (gold vs series at lags -3, -2, -1, 0, +1, +2, +3)
        for (int lag : {-3, -2, -1, 0, 1, 2, 3}) {
            int window = 252;  // 1-year rolling
            if (n < static_cast<size_t>(window + std::abs(lag))) continue;
            
            PriceVec leadlag_corr(n, std::nan(""));
            
            for (size_t i = window + std::abs(lag); i < n; ++i) {
                double sum_x = 0.0, sum_y = 0.0, sum_xy = 0.0, sum_xx = 0.0, sum_yy = 0.0;
                int count = 0;
                
                for (int j = 0; j < window; ++j) {
                    int idx_gold = i - j;
                    int idx_series = i - j + lag;
                    
                    if (idx_series < 0 || idx_series >= static_cast<int>(n)) continue;
                    
                    double x = gold_returns[idx_gold];
                    double y = series_returns[idx_series];
                    
                    if (std::isnan(x) || std::isnan(y)) continue;
                    
                    sum_x += x;
                    sum_y += y;
                    sum_xy += x * y;
                    sum_xx += x * x;
                    sum_yy += y * y;
                    ++count;
                }
                
                if (count < window / 2) continue;
                
                double mean_x = sum_x / count;
                double mean_y = sum_y / count;
                double cov = (sum_xy / count) - mean_x * mean_y;
                double std_x = std::sqrt((sum_xx / count) - mean_x * mean_x);
                double std_y = std::sqrt((sum_yy / count) - mean_y * mean_y);
                
                if (std_x > 1e-9 && std_y > 1e-9) {
                    leadlag_corr[i] = cov / (std_x * std_y);
                }
            }
            
            std::string lag_str = (lag >= 0) ? "plus" + std::to_string(lag) : "minus" + std::to_string(-lag);
            features["leadlag_corr_" + series_id + "_lag_" + lag_str] = leadlag_corr;
        }
    }
    
    // TODO: Granger causality (requires VAR model + F-test)
    // For now: placeholder
    // Granger causality tests if past values of X help predict Y beyond past values of Y alone
    // Implementation requires fitting VAR(p) models and likelihood ratio test
    // Stub: mark as not implemented
    
    features["granger_dxy_to_gold_pvalue"] = PriceVec(gold_returns.size(), std::nan(""));
    features["granger_vix_to_gold_pvalue"] = PriceVec(gold_returns.size(), std::nan(""));
    features["granger_dgs10_to_gold_pvalue"] = PriceVec(gold_returns.size(), std::nan(""));
    
    return features;
}

} // namespace dominion::features
