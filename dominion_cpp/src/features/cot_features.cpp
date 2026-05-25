#include <cmath>
#include "dominion/features.hpp"
#include <algorithm>
#include <numeric>

namespace dominion::features {

FeatureMap compute_cot_features(const std::vector<COTData>& cot, const std::vector<int>& windows) {
    FeatureMap features;
    
    if (cot.empty()) return features;
    
    // Extract time series
    std::vector<double> net_comm, spec_sent, open_int;
    for (const auto& c : cot) {
        net_comm.push_back(static_cast<double>(c.net_commercial));
        spec_sent.push_back(c.speculator_sentiment);
        open_int.push_back(static_cast<double>(c.open_interest));
    }
    
    // Net commercial percentile (52, 104, 252 week windows)
    for (int w : {52, 104, 252}) {
        if (cot.size() < static_cast<size_t>(w)) continue;
        
        PriceVec percentile(cot.size(), std::nan(""));
        for (size_t i = w; i < cot.size(); ++i) {
            std::vector<double> window(net_comm.begin() + i - w, net_comm.begin() + i + 1);
            std::sort(window.begin(), window.end());
            auto it = std::lower_bound(window.begin(), window.end(), net_comm[i]);
            double rank = std::distance(window.begin(), it) / static_cast<double>(window.size());
            percentile[i] = rank * 100.0;
        }
        features["net_commercial_percentile_" + std::to_string(w)] = percentile;
    }
    
    // Speculator sentiment percentile
    for (int w : {52, 104, 252}) {
        if (cot.size() < static_cast<size_t>(w)) continue;
        
        PriceVec percentile(cot.size(), std::nan(""));
        for (size_t i = w; i < cot.size(); ++i) {
            std::vector<double> window(spec_sent.begin() + i - w, spec_sent.begin() + i + 1);
            std::sort(window.begin(), window.end());
            auto it = std::lower_bound(window.begin(), window.end(), spec_sent[i]);
            double rank = std::distance(window.begin(), it) / static_cast<double>(window.size());
            percentile[i] = rank * 100.0;
        }
        features["speculator_sentiment_percentile_" + std::to_string(w)] = percentile;
    }
    
    // Momentum (4, 8, 12 week changes)
    for (int lag : {4, 8, 12}) {
        PriceVec net_comm_momentum = diff(net_comm, lag);
        PriceVec spec_sent_momentum = diff(spec_sent, lag);
        PriceVec oi_momentum = pct_change(open_int, lag);
        
        features["net_commercial_momentum_" + std::to_string(lag)] = net_comm_momentum;
        features["speculator_sentiment_momentum_" + std::to_string(lag)] = spec_sent_momentum;
        features["open_interest_momentum_" + std::to_string(lag)] = oi_momentum;
    }
    
    // Hedger ratio: (comm_long + comm_short) / open_interest
    PriceVec hedger_ratio(cot.size());
    for (size_t i = 0; i < cot.size(); ++i) {
        double total_comm = cot[i].commercial_long + cot[i].commercial_short;
        hedger_ratio[i] = total_comm / (cot[i].open_interest + 1e-9);
    }
    features["hedger_ratio"] = hedger_ratio;
    
    // Spec concentration: (noncomm_long + noncomm_short) / open_interest
    PriceVec spec_conc(cot.size());
    for (size_t i = 0; i < cot.size(); ++i) {
        double total_spec = cot[i].noncommercial_long + cot[i].noncommercial_short;
        spec_conc[i] = total_spec / (cot[i].open_interest + 1e-9);
    }
    features["speculator_concentration"] = spec_conc;
    
    // OI vs average (rolling 52 weeks)
    auto oi_mean_52 = rolling_mean(open_int, 52);
    PriceVec oi_vs_avg(cot.size());
    for (size_t i = 0; i < cot.size(); ++i) {
        oi_vs_avg[i] = open_int[i] / (oi_mean_52[i] + 1e-9);
    }
    features["open_interest_vs_avg_52w"] = oi_vs_avg;
    
    return features;
}

} // namespace dominion::features
