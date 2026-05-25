#include "dominion/features.hpp"
#include <cmath>
#include <algorithm>
#include <numeric>
#include <Eigen/Dense>

namespace dominion::features {

// Feature #36: DCC-GARCH dynamic correlation (simplified via EWMA)
// Full DCC requires MLE; here we use exponentially weighted correlation
FeatureMap compute_dcc_correlations(const PriceVec& gold_returns,
                                    const std::unordered_map<std::string, PriceVec>& macro_returns,
                                    double lambda) {
    FeatureMap result;
    if (gold_returns.empty()) return result;

    size_t n = gold_returns.size();

    for (const auto& [series_name, macro_ret] : macro_returns) {
        if (macro_ret.size() != n) continue;

        // EWMA covariance
        double ewma_cov = 0.0;
        double ewma_var_gold = 0.0;
        double ewma_var_macro = 0.0;

        PriceVec dcc(n, std::nan(""));

        for (size_t i = 1; i < n; ++i) {
            if (std::isnan(gold_returns[i]) || std::isnan(macro_ret[i])) continue;

            // Update EWMA variances and covariance
            ewma_var_gold = lambda * ewma_var_gold + (1 - lambda) * gold_returns[i] * gold_returns[i];
            ewma_var_macro = lambda * ewma_var_macro + (1 - lambda) * macro_ret[i] * macro_ret[i];
            ewma_cov = lambda * ewma_cov + (1 - lambda) * gold_returns[i] * macro_ret[i];

            // Dynamic correlation
            double denom = std::sqrt(ewma_var_gold * ewma_var_macro + 1e-9);
            dcc[i] = (denom > 1e-9) ? ewma_cov / denom : 0.0;
        }

        result["dcc_gold_" + series_name] = dcc;

        // DCC z-score (deviation from long-term mean)
        auto dcc_mean = rolling_mean(dcc, 252);
        auto dcc_std = rolling_std(dcc, 252);
        PriceVec dcc_z(n);
        for (size_t i = 0; i < n; ++i) {
            dcc_z[i] = (dcc_std[i] > 1e-9) ? (dcc[i] - dcc_mean[i]) / dcc_std[i] : 0.0;
        }
        result["dcc_gold_" + series_name + "_zscore"] = dcc_z;
    }

    return result;
}

// Feature #37: Copula tail dependence (Kendall's tau for tail events)
// Measures correlation in extreme moves
FeatureMap compute_copula_tail_dependence(const PriceVec& gold_returns,
                                          const std::unordered_map<std::string, PriceVec>& macro_returns,
                                          double tail_quantile,
                                          int window) {
    FeatureMap result;
    if (gold_returns.empty()) return result;

    size_t n = gold_returns.size();

    for (const auto& [series_name, macro_ret] : macro_returns) {
        if (macro_ret.size() != n) continue;

        PriceVec upper_tail_dep(n, std::nan(""));
        PriceVec lower_tail_dep(n, std::nan(""));

        for (int i = window; i < static_cast<int>(n); ++i) {
            // Extract window
            std::vector<std::pair<double, double>> pairs;
            for (int t = i - window; t < i; ++t) {
                if (!std::isnan(gold_returns[t]) && !std::isnan(macro_ret[t])) {
                    pairs.push_back({gold_returns[t], macro_ret[t]});
                }
            }

            if (pairs.size() < static_cast<size_t>(window / 2)) continue;

            // Compute empirical quantiles
            std::vector<double> gold_sorted, macro_sorted;
            for (const auto& p : pairs) {
                gold_sorted.push_back(p.first);
                macro_sorted.push_back(p.second);
            }
            std::sort(gold_sorted.begin(), gold_sorted.end());
            std::sort(macro_sorted.begin(), macro_sorted.end());

            size_t upper_idx = static_cast<size_t>(pairs.size() * (1.0 - tail_quantile));
            size_t lower_idx = static_cast<size_t>(pairs.size() * tail_quantile);

            double gold_upper = gold_sorted[upper_idx];
            double gold_lower = gold_sorted[lower_idx];
            double macro_upper = macro_sorted[upper_idx];
            double macro_lower = macro_sorted[lower_idx];

            // Count joint exceedances
            int upper_joint = 0, lower_joint = 0;
            for (const auto& p : pairs) {
                if (p.first > gold_upper && p.second > macro_upper) upper_joint++;
                if (p.first < gold_lower && p.second < macro_lower) lower_joint++;
            }

            upper_tail_dep[i] = static_cast<double>(upper_joint) / (pairs.size() * tail_quantile);
            lower_tail_dep[i] = static_cast<double>(lower_joint) / (pairs.size() * tail_quantile);
        }

        result["upper_tail_dep_gold_" + series_name] = upper_tail_dep;
        result["lower_tail_dep_gold_" + series_name] = lower_tail_dep;

        // Tail asymmetry
        PriceVec tail_asymmetry(n);
        for (size_t i = 0; i < n; ++i) {
            tail_asymmetry[i] = upper_tail_dep[i] - lower_tail_dep[i];
        }
        result["tail_asymmetry_gold_" + series_name] = tail_asymmetry;
    }

    return result;
}

// Feature #38: PCA regime identification (first principal component regime breaks)
FeatureMap compute_pca_regime_features(const std::unordered_map<std::string, PriceVec>& macro_returns,
                                       int window) {
    FeatureMap result;
    if (macro_returns.empty()) return result;

    // Build matrix of returns
    size_t n_series = macro_returns.size();
    size_t n_samples = macro_returns.begin()->second.size();

    std::vector<std::string> series_names;
    std::vector<std::vector<double>> returns_matrix(n_series);
    size_t idx = 0;
    for (const auto& [name, rets] : macro_returns) {
        series_names.push_back(name);
        returns_matrix[idx++] = rets;
    }

    PriceVec pc1_loading(n_samples, std::nan(""));
    PriceVec pc1_explained_var(n_samples, std::nan(""));

    for (int i = window; i < static_cast<int>(n_samples); ++i) {
        // Build covariance matrix for window
        Eigen::MatrixXd cov(n_series, n_series);

        for (size_t j = 0; j < n_series; ++j) {
            for (size_t k = 0; k < n_series; ++k) {
                double sum = 0.0;
                int count = 0;
                for (int t = i - window; t < i; ++t) {
                    if (!std::isnan(returns_matrix[j][t]) && !std::isnan(returns_matrix[k][t])) {
                        sum += returns_matrix[j][t] * returns_matrix[k][t];
                        count++;
                    }
                }
                cov(j, k) = (count > 0) ? sum / count : 0.0;
            }
        }

        // Eigen decomposition
        Eigen::SelfAdjointEigenSolver<Eigen::MatrixXd> solver(cov);
        Eigen::VectorXd eigenvalues = solver.eigenvalues();
        Eigen::MatrixXd eigenvectors = solver.eigenvectors();

        // Largest eigenvalue (last in Eigen's ordering)
        double pc1_eigenval = eigenvalues(n_series - 1);
        Eigen::VectorXd pc1_eigenvec = eigenvectors.col(n_series - 1);

        // Project current returns onto PC1
        double projection = 0.0;
        for (size_t j = 0; j < n_series; ++j) {
            if (!std::isnan(returns_matrix[j][i])) {
                projection += pc1_eigenvec(j) * returns_matrix[j][i];
            }
        }
        pc1_loading[i] = projection;

        // Explained variance ratio
        double total_var = eigenvalues.sum();
        pc1_explained_var[i] = (total_var > 0) ? pc1_eigenval / total_var : 0.0;
    }

    result["pca_pc1_loading"] = pc1_loading;
    result["pca_pc1_explained_var"] = pc1_explained_var;

    // PC1 regime breaks (when explained variance drops sharply)
    auto pc1_var_diff = diff(pc1_explained_var, 1);
    result["pca_regime_break_signal"] = pc1_var_diff;

    return result;
}

// Feature #40: Network centrality (correlation network analysis)
// Measures gold's centrality in macro correlation network
FeatureMap compute_network_centrality(const PriceVec& gold_returns,
                                      const std::unordered_map<std::string, PriceVec>& macro_returns,
                                      double corr_threshold,
                                      int window) {
    FeatureMap result;
    if (gold_returns.empty() || macro_returns.empty()) return result;

    size_t n = gold_returns.size();
    PriceVec degree_centrality(n, std::nan(""));
    PriceVec eigenvector_centrality(n, std::nan(""));

    for (int i = window; i < static_cast<int>(n); ++i) {
        // Build correlation matrix
        std::vector<std::string> node_names = {"gold"};
        std::vector<PriceVec> node_returns = {gold_returns};

        for (const auto& [name, rets] : macro_returns) {
            node_names.push_back(name);
            node_returns.push_back(rets);
        }

        size_t n_nodes = node_returns.size();
        Eigen::MatrixXd corr_matrix(n_nodes, n_nodes);

        for (size_t j = 0; j < n_nodes; ++j) {
            for (size_t k = 0; k < n_nodes; ++k) {
                double sum_xy = 0.0, sum_x = 0.0, sum_y = 0.0;
                double sum_xx = 0.0, sum_yy = 0.0;
                int count = 0;

                for (int t = i - window; t < i; ++t) {
                    if (!std::isnan(node_returns[j][t]) && !std::isnan(node_returns[k][t])) {
                        sum_x += node_returns[j][t];
                        sum_y += node_returns[k][t];
                        sum_xy += node_returns[j][t] * node_returns[k][t];
                        sum_xx += node_returns[j][t] * node_returns[j][t];
                        sum_yy += node_returns[k][t] * node_returns[k][t];
                        count++;
                    }
                }

                if (count > 0) {
                    double mean_x = sum_x / count;
                    double mean_y = sum_y / count;
                    double cov = (sum_xy / count) - mean_x * mean_y;
                    double std_x = std::sqrt((sum_xx / count) - mean_x * mean_x + 1e-9);
                    double std_y = std::sqrt((sum_yy / count) - mean_y * mean_y + 1e-9);
                    corr_matrix(j, k) = cov / (std_x * std_y);
                } else {
                    corr_matrix(j, k) = (j == k) ? 1.0 : 0.0;
                }
            }
        }

        // Degree centrality: count edges above threshold
        int degree = 0;
        for (size_t k = 1; k < n_nodes; ++k) {  // Skip gold-gold
            if (std::abs(corr_matrix(0, k)) > corr_threshold) {
                degree++;
            }
        }
        degree_centrality[i] = static_cast<double>(degree) / (n_nodes - 1);

        // Eigenvector centrality: dominant eigenvector of correlation matrix
        Eigen::SelfAdjointEigenSolver<Eigen::MatrixXd> solver(corr_matrix);
        Eigen::VectorXd eigenvec = solver.eigenvectors().col(n_nodes - 1);
        eigenvector_centrality[i] = std::abs(eigenvec(0));  // Gold's component
    }

    result["network_degree_centrality"] = degree_centrality;
    result["network_eigenvector_centrality"] = eigenvector_centrality;

    return result;
}

} // namespace dominion::features
