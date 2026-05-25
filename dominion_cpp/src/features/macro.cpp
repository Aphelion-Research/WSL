#include <cmath>
#include "dominion/features.hpp"
#include <algorithm>

namespace dominion::features {

FeatureMap compute_macro_features(const PriceVec& gold_close,
                                  const std::unordered_map<std::string, PriceVec>& macro_series,
                                  const std::vector<std::string>& fomc_dates) {
    FeatureMap features;
    
    // Real yield (10Y TIPS)
    if (macro_series.find("DFII10") != macro_series.end()) {
        const auto& tips = macro_series.at("DFII10");
        features["real_yield_level"] = tips;
        
        // Changes (1d, 5d, 20d)
        features["real_yield_change_1d"] = diff(tips, 1);
        features["real_yield_change_5d"] = diff(tips, 5);
        features["real_yield_change_20d"] = diff(tips, 20);
    }
    
    // Yield curve slope (10Y - 2Y)
    if (macro_series.find("DGS10") != macro_series.end() && 
        macro_series.find("DGS2") != macro_series.end()) {
        const auto& y10 = macro_series.at("DGS10");
        const auto& y2 = macro_series.at("DGS2");
        
        PriceVec slope(y10.size());
        for (size_t i = 0; i < y10.size(); ++i) {
            slope[i] = y10[i] - y2[i];
        }
        features["yield_curve_slope"] = slope;
        features["yield_curve_slope_change_5d"] = diff(slope, 5);
        features["yield_curve_slope_change_20d"] = diff(slope, 20);
        
        // Inverted yield curve flag
        PriceVec inverted(slope.size());
        for (size_t i = 0; i < slope.size(); ++i) {
            inverted[i] = (slope[i] < 0.0) ? 1.0 : 0.0;
        }
        features["yield_curve_inverted"] = inverted;
    }
    
    // Breakeven inflation (5Y5Y forward)
    if (macro_series.find("T5YIFR") != macro_series.end()) {
        const auto& breakeven = macro_series.at("T5YIFR");
        features["breakeven_inflation_level"] = breakeven;
        features["breakeven_inflation_change_1d"] = diff(breakeven, 1);
        features["breakeven_inflation_change_20d"] = diff(breakeven, 20);
    }
    
    // DXY momentum
    if (macro_series.find("DTWEXBGS") != macro_series.end()) {
        const auto& dxy = macro_series.at("DTWEXBGS");
        
        // Percent changes at multiple windows
        for (int w : {5, 10, 20, 50}) {
            features["dxy_pct_change_" + std::to_string(w)] = pct_change(dxy, w);
        }
        
        // Z-score (deviation from 252-bar mean)
        auto dxy_mean = rolling_mean(dxy, 252);
        auto dxy_std = rolling_std(dxy, 252);
        PriceVec dxy_zscore(dxy.size());
        for (size_t i = 0; i < dxy.size(); ++i) {
            if (dxy_std[i] > 1e-9) {
                dxy_zscore[i] = (dxy[i] - dxy_mean[i]) / dxy_std[i];
            } else {
                dxy_zscore[i] = 0.0;
            }
        }
        features["dxy_zscore_252"] = dxy_zscore;
    }
    
    // Fed funds rate
    if (macro_series.find("FEDFUNDS") != macro_series.end()) {
        const auto& fedfunds = macro_series.at("FEDFUNDS");
        features["fed_funds_rate"] = fedfunds;
        
        // 1-month and 3-month changes
        features["fed_funds_change_1m"] = diff(fedfunds, 21);  // ~21 trading days
        features["fed_funds_change_3m"] = diff(fedfunds, 63);
    }
    
    // CPI (Consumer Price Index)
    if (macro_series.find("CPIAUCSL") != macro_series.end()) {
        const auto& cpi = macro_series.at("CPIAUCSL");
        
        // YoY change (252 trading days ~ 1 year)
        features["cpi_yoy"] = pct_change(cpi, 252);
        
        // MoM change (21 trading days ~ 1 month)
        features["cpi_mom"] = pct_change(cpi, 21);
    }
    
    // VIX level and changes
    if (macro_series.find("VIXCLS") != macro_series.end()) {
        const auto& vix = macro_series.at("VIXCLS");
        features["vix_level"] = vix;
        features["vix_change_1d"] = diff(vix, 1);
        features["vix_change_5d"] = diff(vix, 5);
        
        // VIX z-score
        auto vix_mean = rolling_mean(vix, 252);
        auto vix_std = rolling_std(vix, 252);
        PriceVec vix_zscore(vix.size());
        for (size_t i = 0; i < vix.size(); ++i) {
            if (vix_std[i] > 1e-9) {
                vix_zscore[i] = (vix[i] - vix_mean[i]) / vix_std[i];
            } else {
                vix_zscore[i] = 0.0;
            }
        }
        features["vix_zscore_252"] = vix_zscore;
    }
    
    // Real gold price (nominal / CPI * 100)
    if (macro_series.find("CPIAUCSL") != macro_series.end() && !gold_close.empty()) {
        const auto& cpi = macro_series.at("CPIAUCSL");
        
        PriceVec real_gold(std::min(gold_close.size(), cpi.size()));
        for (size_t i = 0; i < real_gold.size(); ++i) {
            if (cpi[i] > 1e-9) {
                real_gold[i] = gold_close[i] / (cpi[i] / 100.0);
            } else {
                real_gold[i] = gold_close[i];
            }
        }
        features["real_gold_price"] = real_gold;
    }
    
    // 10Y-2Y spread (alternative to slope above)
    if (macro_series.find("T10Y2Y") != macro_series.end()) {
        const auto& spread = macro_series.at("T10Y2Y");
        features["treasury_spread_10y2y"] = spread;
        features["treasury_spread_change_20d"] = diff(spread, 20);
    }
    
    return features;
}

} // namespace dominion::features
