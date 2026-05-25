#pragma once

#include "dominion/config.hpp"
#include "dominion/types.hpp"

#include <array>
#include <string>
#include <unordered_map>
#include <vector>

namespace dominion {

struct KalmanState {
    std::array<double, 2> x = {0.0, 0.0};  // [price, velocity]
    std::array<std::array<double, 2>, 2> P = {{{1000.0, 0.0}, {0.0, 1000.0}}};
    bool initialized = false;
};

struct FusionResult {
    double fused_price;
    double confidence;
    std::unordered_map<std::string, double> source_weights;
    bool anomaly_flag;
};

class KalmanFilter {
public:
    KalmanFilter(double process_noise, double observation_noise);

    void predict();
    void update(double observation, double trust_weight = 1.0);
    double price() const { return state_.x[0]; }
    double velocity() const { return state_.x[1]; }
    double uncertainty() const { return state_.P[0][0]; }
    bool initialized() const { return state_.initialized; }

private:
    double q_;  // process noise
    double r_;  // observation noise
    KalmanState state_;
};

class KalmanFilterBank {
public:
    explicit KalmanFilterBank(const std::unordered_map<std::string, KalmanConfig>& configs);

    FusionResult fuse(const std::unordered_map<std::string, double>& observations);
    void update_trust(const std::string& source, double innovation, double uncertainty);

    const std::unordered_map<std::string, double>& trust_scores() const { return trust_scores_; }

private:
    std::unordered_map<std::string, KalmanFilter> filters_;
    std::unordered_map<std::string, double> trust_scores_;
};

struct SyntheticTick {
    Timestamp timestamp;
    double price;
    double confidence;
};

std::vector<SyntheticTick> brownian_bridge(
    double open, double high, double low, double close,
    Timestamp start, Timestamp end,
    int n_ticks = 100, double sigma = 0.01
);

struct ConflictResult {
    double resolved_price;
    std::vector<std::string> quarantined_sources;
    bool byzantine_detected;
};

ConflictResult resolve_conflict(
    const std::unordered_map<std::string, double>& observations,
    double fused_price,
    double confidence,
    const std::unordered_map<std::string, double>& trust_scores
);

} // namespace dominion
