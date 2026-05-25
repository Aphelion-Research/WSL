#include "dominion/health.hpp"
#include <cmath>

namespace dominion {

AnomalyDetector::AnomalyDetector(double z_flag, double z_quarantine)
    : z_flag_(z_flag), z_quarantine_(z_quarantine) {}

AnomalyDetector::PriceAnomaly AnomalyDetector::detect_price_anomaly(
    double price, double mean, double std
) {
    double z = std::abs(price - mean) / (std + 1e-9);
    return {z > z_flag_, z > z_quarantine_, z};
}

bool AnomalyDetector::detect_volume_anomaly(
    double volume, double mean, double std, double threshold
) {
    double z = std::abs(volume - mean) / (std + 1e-9);
    return z > threshold;
}

bool AnomalyDetector::detect_source_divergence(
    const std::unordered_map<std::string, double>& prices,
    double sigma_threshold
) {
    // TODO: Compute std of observations, check if > threshold * avg(uncertainty)
    return false;
}

} // namespace dominion
