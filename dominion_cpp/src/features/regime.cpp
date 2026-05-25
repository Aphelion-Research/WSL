#include <cmath>
#include "dominion/features.hpp"
#include <ctime>

namespace dominion::features {

FeatureMap compute_regime_features(const PriceVec& returns, const PriceVec& volatility,
                                   const PriceVec& volume,
                                   const std::vector<Timestamp>& timestamps) {
    FeatureMap features;
    
    if (timestamps.empty()) return features;
    
    // Time-based micro regime (london/ny/asian/overlap/dead_zone)
    PriceVec regime_london(timestamps.size(), 0.0);
    PriceVec regime_ny(timestamps.size(), 0.0);
    PriceVec regime_asian(timestamps.size(), 0.0);
    PriceVec regime_overlap(timestamps.size(), 0.0);
    PriceVec regime_dead_zone(timestamps.size(), 0.0);
    
    for (size_t i = 0; i < timestamps.size(); ++i) {
        auto t = std::chrono::system_clock::to_time_t(timestamps[i]);
        std::tm* tm = std::gmtime(&t);
        int hour = tm->tm_hour;  // UTC hour
        
        // London: 07:00-16:00 UTC
        if (hour >= 7 && hour < 16) {
            regime_london[i] = 1.0;
        }
        
        // NY: 12:00-21:00 UTC
        if (hour >= 12 && hour < 21) {
            regime_ny[i] = 1.0;
        }
        
        // Asian: 23:00-08:00 UTC (wraps around)
        if (hour >= 23 || hour < 8) {
            regime_asian[i] = 1.0;
        }
        
        // Overlap (London + NY): 12:00-16:00 UTC
        if (hour >= 12 && hour < 16) {
            regime_overlap[i] = 1.0;
        }
        
        // Dead zone (Asian close to London open): 08:00-09:00 UTC
        if (hour >= 8 && hour < 9) {
            regime_dead_zone[i] = 1.0;
        }
    }
    
    features["regime_london"] = regime_london;
    features["regime_ny"] = regime_ny;
    features["regime_asian"] = regime_asian;
    features["regime_overlap"] = regime_overlap;
    features["regime_dead_zone"] = regime_dead_zone;
    
    // Simple volatility regime (high vs low based on rolling 20-bar median)
    if (!volatility.empty()) {
        PriceVec vol_regime_high(volatility.size(), 0.0);
        PriceVec vol_regime_low(volatility.size(), 0.0);
        
        for (size_t i = 20; i < volatility.size(); ++i) {
            std::vector<double> window(volatility.begin() + i - 20, volatility.begin() + i);
            std::sort(window.begin(), window.end());
            double median = window[window.size() / 2];
            
            if (volatility[i] > median * 1.2) {
                vol_regime_high[i] = 1.0;
            } else if (volatility[i] < median * 0.8) {
                vol_regime_low[i] = 1.0;
            }
        }
        
        features["regime_vol_high"] = vol_regime_high;
        features["regime_vol_low"] = vol_regime_low;
    }
    
    // Trend regime based on moving average crossover
    if (!returns.empty()) {
        auto ma_fast = ema(returns, 10);
        auto ma_slow = ema(returns, 50);
        
        PriceVec regime_trending_up(returns.size(), 0.0);
        PriceVec regime_trending_down(returns.size(), 0.0);
        PriceVec regime_ranging(returns.size(), 0.0);
        
        for (size_t i = 50; i < returns.size(); ++i) {
            double diff = ma_fast[i] - ma_slow[i];
            
            if (diff > 0.0001) {
                regime_trending_up[i] = 1.0;
            } else if (diff < -0.0001) {
                regime_trending_down[i] = 1.0;
            } else {
                regime_ranging[i] = 1.0;
            }
        }
        
        features["regime_trending_up"] = regime_trending_up;
        features["regime_trending_down"] = regime_trending_down;
        features["regime_ranging"] = regime_ranging;
    }
    
    // TODO: HMM-based tactical regime (requires Python bridge or native Baum-Welch)
    // For now: stub placeholder
    PriceVec regime_hmm_state(timestamps.size(), std::nan(""));
    features["regime_hmm_tactical"] = regime_hmm_state;
    
    return features;
}

} // namespace dominion::features
