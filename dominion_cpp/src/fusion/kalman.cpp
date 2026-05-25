#include "dominion/fusion.hpp"
#include <cmath>
#include <algorithm>
#include <numeric>

namespace dominion {

KalmanFilter::KalmanFilter(double process_noise, double observation_noise)
    : q_(process_noise), r_(observation_noise) {}

void KalmanFilter::predict() {
    if (!state_.initialized) return;

    // State transition: x = F * x
    // F = [[1, 1], [0, 1]]  (constant velocity model)
    double new_price = state_.x[0] + state_.x[1];
    double new_velocity = state_.x[1];
    state_.x[0] = new_price;
    state_.x[1] = new_velocity;

    // Covariance update: P = F * P * F^T + Q
    // Q = [[q, 0], [0, q]]
    auto& P = state_.P;
    double p00 = P[0][0] + 2 * P[0][1] + P[1][1] + q_;
    double p01 = P[0][1] + P[1][1];
    double p10 = p01;
    double p11 = P[1][1] + q_;
    P[0][0] = p00;
    P[0][1] = p01;
    P[1][0] = p10;
    P[1][1] = p11;
}

void KalmanFilter::update(double observation, double trust_weight) {
    if (!state_.initialized) {
        state_.x[0] = observation;
        state_.x[1] = 0.0;
        state_.initialized = true;
        return;
    }

    // Innovation: y = z - H * x
    // H = [[1, 0]]  (observe price only)
    double innovation = observation - state_.x[0];

    // Innovation covariance: S = H * P * H^T + R
    double S = state_.P[0][0] + r_ / trust_weight;

    // Kalman gain: K = P * H^T * S^-1
    double k0 = state_.P[0][0] / S;
    double k1 = state_.P[1][0] / S;

    // State update: x = x + K * y
    state_.x[0] += k0 * innovation;
    state_.x[1] += k1 * innovation;

    // Covariance update: P = (I - K * H) * P
    auto& P = state_.P;
    double p00 = (1.0 - k0) * P[0][0];
    double p01 = (1.0 - k0) * P[0][1];
    double p10 = P[1][0] - k1 * P[0][0];
    double p11 = P[1][1] - k1 * P[0][1];
    P[0][0] = p00;
    P[0][1] = p01;
    P[1][0] = p10;
    P[1][1] = p11;
}

KalmanFilterBank::KalmanFilterBank(const std::unordered_map<std::string, KalmanConfig>& configs) {
    for (const auto& [name, cfg] : configs) {
        filters_.emplace(name, KalmanFilter(cfg.process_noise, cfg.observation_noise));
    }
}

FusionResult KalmanFilterBank::fuse(const std::unordered_map<std::string, double>& observations) {
    // Initialize trust scores if empty
    for (const auto& [source, price] : observations) {
        if (trust_scores_.find(source) == trust_scores_.end()) {
            trust_scores_[source] = 0.5;  // neutral start
        }
    }

    // Step 1: Predict all filters
    for (auto& [name, filter] : filters_) {
        filter.predict();
    }

    // Step 2: Update each filter with each observation (trust-weighted)
    std::unordered_map<std::string, double> innovations;
    for (const auto& [source, price] : observations) {
        double trust = trust_scores_[source];
        for (auto& [name, filter] : filters_) {
            filter.update(price, trust);
        }

        // Track innovation for trust update
        double avg_prediction = 0.0;
        for (const auto& [name, filter] : filters_) {
            if (filter.initialized()) {
                avg_prediction += filter.price();
            }
        }
        avg_prediction /= filters_.size();
        innovations[source] = price - avg_prediction;
    }

    // Step 3: Fuse filter outputs (inverse-uncertainty weighting)
    double sum_weighted_price = 0.0;
    double sum_weights = 0.0;
    for (const auto& [name, filter] : filters_) {
        if (filter.initialized()) {
            double weight = 1.0 / (filter.uncertainty() + 1e-9);
            sum_weighted_price += filter.price() * weight;
            sum_weights += weight;
        }
    }
    double fused_price = sum_weighted_price / (sum_weights + 1e-9);
    double confidence = 1.0 / (1.0 + std::sqrt(sum_weights / filters_.size()));

    // Step 4: Compute source weights (by trust score)
    std::unordered_map<std::string, double> source_weights;
    double trust_sum = 0.0;
    for (const auto& [source, trust] : trust_scores_) {
        trust_sum += trust;
    }
    for (const auto& [source, trust] : trust_scores_) {
        source_weights[source] = trust / (trust_sum + 1e-9);
    }

    // Step 5: Update trust scores based on innovations
    for (const auto& [source, innovation] : innovations) {
        double avg_uncertainty = 0.0;
        for (const auto& [name, filter] : filters_) {
            if (filter.initialized()) {
                avg_uncertainty += filter.uncertainty();
            }
        }
        avg_uncertainty /= filters_.size();
        update_trust(source, innovation, avg_uncertainty);
    }

    // Step 6: Detect anomalies (any source >3σ from fused)
    bool anomaly_flag = false;
    for (const auto& [source, price] : observations) {
        double z = std::abs(price - fused_price) / (confidence + 1e-9);
        if (z > 3.0) {
            anomaly_flag = true;
            break;
        }
    }

    return {fused_price, confidence, source_weights, anomaly_flag};
}

void KalmanFilterBank::update_trust(const std::string& source, double innovation, double uncertainty) {
    double z_score = std::abs(innovation) / (std::sqrt(uncertainty) + 1e-9);
    double& trust = trust_scores_[source];

    if (z_score < 1.0) {
        trust = std::min(0.95, trust + 0.01);  // increase trust
    } else if (z_score > 3.0) {
        trust = std::max(0.05, trust - 0.05);  // decrease trust
    }
}

} // namespace dominion
