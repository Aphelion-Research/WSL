#include "dominion/features.hpp"
#include <cmath>
#include <algorithm>
#include <numeric>
#include <random>

namespace dominion::features {

// Feature #51: Autoencoder reconstruction error (VAE-style anomaly detection)
// Uses PCA as lightweight proxy for autoencoder
FeatureMap compute_autoencoder_anomalies(const FeatureMap& input_features,
                                         const std::vector<std::string>& feature_names,
                                         int n_components) {
    FeatureMap result;

    if (input_features.empty() || feature_names.empty()) return result;

    size_t n_samples = input_features.begin()->second.size();
    size_t n_features = feature_names.size();

    // Build feature matrix (n_samples × n_features)
    std::vector<std::vector<double>> X(n_samples, std::vector<double>(n_features, 0.0));

    for (size_t j = 0; j < n_features; ++j) {
        if (input_features.find(feature_names[j]) == input_features.end()) continue;
        const auto& feat = input_features.at(feature_names[j]);
        for (size_t i = 0; i < n_samples; ++i) {
            X[i][j] = std::isnan(feat[i]) ? 0.0 : feat[i];
        }
    }

    // Normalize columns (zero mean, unit variance)
    std::vector<double> means(n_features, 0.0);
    std::vector<double> stds(n_features, 0.0);

    for (size_t j = 0; j < n_features; ++j) {
        double sum = 0.0;
        for (size_t i = 0; i < n_samples; ++i) sum += X[i][j];
        means[j] = sum / n_samples;

        double sum_sq = 0.0;
        for (size_t i = 0; i < n_samples; ++i) {
            X[i][j] -= means[j];
            sum_sq += X[i][j] * X[i][j];
        }
        stds[j] = std::sqrt(sum_sq / n_samples + 1e-9);

        for (size_t i = 0; i < n_samples; ++i) {
            X[i][j] /= stds[j];
        }
    }

    // Simplified PCA: compute covariance matrix eigenvalues (power iteration for top components)
    // Full implementation would use SVD, here we use rolling window reconstruction error

    // Rolling reconstruction error: measure how well point fits local covariance structure
    PriceVec reconstruction_error(n_samples, std::nan(""));
    int window = 252;  // 1 year lookback

    for (int i = window; i < static_cast<int>(n_samples); ++i) {
        // Compute local mean
        std::vector<double> local_mean(n_features, 0.0);
        for (int t = i - window; t < i; ++t) {
            for (size_t j = 0; j < n_features; ++j) {
                local_mean[j] += X[t][j];
            }
        }
        for (size_t j = 0; j < n_features; ++j) local_mean[j] /= window;

        // Reconstruction error = squared distance from local mean (simplified)
        double error = 0.0;
        for (size_t j = 0; j < n_features; ++j) {
            double diff = X[i][j] - local_mean[j];
            error += diff * diff;
        }
        reconstruction_error[i] = std::sqrt(error / n_features);
    }

    result["autoencoder_reconstruction_error"] = reconstruction_error;

    // Z-score of reconstruction error
    auto error_mean = rolling_mean(reconstruction_error, 60);
    auto error_std = rolling_std(reconstruction_error, 60);
    PriceVec reconstruction_z(n_samples);
    for (size_t i = 0; i < n_samples; ++i) {
        reconstruction_z[i] = (error_std[i] > 1e-9) ?
            (reconstruction_error[i] - error_mean[i]) / error_std[i] : 0.0;
    }
    result["autoencoder_anomaly_zscore"] = reconstruction_z;

    return result;
}

// Feature #96: Feature stability tracking (rolling IC variance)
FeatureMap compute_feature_stability(const FeatureMap& features,
                                     const PriceVec& returns,
                                     int window) {
    FeatureMap result;

    if (features.empty() || returns.empty()) return result;
    size_t n = returns.size();

    // For each feature, compute rolling IC (correlation with forward returns)
    // Then compute variance of IC over time

    for (const auto& [feat_name, feat_values] : features) {
        if (feat_values.size() != n) continue;

        // Compute rolling IC
        PriceVec ic_series(n, std::nan(""));

        for (int i = window; i < static_cast<int>(n) - 1; ++i) {
            // IC = correlation between feature[t] and return[t+1] over rolling window
            double sum_x = 0.0, sum_y = 0.0, sum_xy = 0.0;
            double sum_xx = 0.0, sum_yy = 0.0;
            int count = 0;

            for (int t = i - window; t < i; ++t) {
                if (std::isnan(feat_values[t]) || std::isnan(returns[t+1])) continue;
                sum_x += feat_values[t];
                sum_y += returns[t+1];
                sum_xy += feat_values[t] * returns[t+1];
                sum_xx += feat_values[t] * feat_values[t];
                sum_yy += returns[t+1] * returns[t+1];
                count++;
            }

            if (count < window / 2) continue;

            double mean_x = sum_x / count;
            double mean_y = sum_y / count;
            double cov = (sum_xy / count) - mean_x * mean_y;
            double std_x = std::sqrt((sum_xx / count) - mean_x * mean_x + 1e-9);
            double std_y = std::sqrt((sum_yy / count) - mean_y * mean_y + 1e-9);

            ic_series[i] = cov / (std_x * std_y);
        }

        // Compute IC volatility (rolling std of IC)
        auto ic_vol = rolling_std(ic_series, 20);
        result[feat_name + "_stability_ic_vol"] = ic_vol;

        // IC trend (rolling mean of IC)
        auto ic_trend = rolling_mean(ic_series, 60);
        result[feat_name + "_stability_ic_trend"] = ic_trend;
    }

    return result;
}

// Feature #97: Data quality score
FeatureMap compute_data_quality_score(const std::vector<Bar>& bars) {
    FeatureMap result;
    if (bars.empty()) return result;

    size_t n = bars.size();
    PriceVec quality_score(n);
    PriceVec nan_count(n);
    PriceVec outlier_count(n);
    PriceVec gap_indicator(n);

    int window = 60;  // 1 hour for minute bars

    for (int i = window; i < static_cast<int>(n); ++i) {
        // Count NaNs in window
        int nans = 0;
        int outliers = 0;
        int gaps = 0;

        // Collect prices for outlier detection
        std::vector<double> prices;
        for (int t = i - window; t < i; ++t) {
            if (std::isnan(bars[t].close)) {
                nans++;
            } else {
                prices.push_back(bars[t].close);
            }

            // Check for gaps (>5 minute timestamp jump)
            if (t > 0) {
                auto gap = std::chrono::duration_cast<std::chrono::minutes>(
                    bars[t].timestamp - bars[t-1].timestamp).count();
                if (gap > 5) gaps++;
            }
        }

        // Outlier detection: z-score > 5
        if (!prices.empty()) {
            double sum = std::accumulate(prices.begin(), prices.end(), 0.0);
            double mean = sum / prices.size();
            double sq_sum = 0.0;
            for (double p : prices) sq_sum += (p - mean) * (p - mean);
            double std = std::sqrt(sq_sum / prices.size() + 1e-9);

            for (double p : prices) {
                if (std::abs((p - mean) / std) > 5.0) outliers++;
            }
        }

        nan_count[i] = static_cast<double>(nans);
        outlier_count[i] = static_cast<double>(outliers);
        gap_indicator[i] = static_cast<double>(gaps);

        // Quality score: 100 - penalties
        double nan_penalty = (nans * 100.0) / window;
        double outlier_penalty = (outliers * 50.0) / window;
        double gap_penalty = (gaps * 20.0) / window;

        quality_score[i] = std::max(0.0, 100.0 - nan_penalty - outlier_penalty - gap_penalty);
    }

    result["data_quality_score"] = quality_score;
    result["data_quality_nan_count"] = nan_count;
    result["data_quality_outlier_count"] = outlier_count;
    result["data_quality_gap_count"] = gap_indicator;

    return result;
}

} // namespace dominion::features
