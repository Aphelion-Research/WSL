#include "dominion/noise.hpp"
#include <Eigen/Dense>
#include <Eigen/SVD>
#include <cmath>

namespace dominion::noise {

SSAResult compute_ssa(const PriceVec& prices, int window_length, int n_components) {
    SSAResult result;
    const int N = prices.size();
    const int K = N - window_length + 1;

    if (K <= 0 || window_length > N / 2) {
        return result; // Invalid params
    }

    // Build trajectory matrix (Hankel matrix)
    Eigen::MatrixXd trajectory(window_length, K);
    for (int i = 0; i < K; ++i) {
        for (int j = 0; j < window_length; ++j) {
            trajectory(j, i) = prices[i + j];
        }
    }

    // SVD decomposition
    Eigen::JacobiSVD<Eigen::MatrixXd> svd(
        trajectory, Eigen::ComputeThinU | Eigen::ComputeThinV
    );

    result.singular_values = std::vector<double>(
        svd.singularValues().data(),
        svd.singularValues().data() + svd.singularValues().size()
    );

    // Compute explained variance
    double total_variance = 0.0;
    for (double sv : result.singular_values) {
        total_variance += sv * sv;
    }

    result.explained_variance.resize(result.singular_values.size());
    for (size_t i = 0; i < result.singular_values.size(); ++i) {
        double var = result.singular_values[i] * result.singular_values[i];
        result.explained_variance[i] = var / total_variance;
    }

    // Reconstruct components (diagonal averaging)
    n_components = std::min(n_components, static_cast<int>(result.singular_values.size()));
    result.components.resize(n_components);

    for (int comp = 0; comp < n_components; ++comp) {
        Eigen::VectorXd U_col = svd.matrixU().col(comp);
        Eigen::VectorXd V_col = svd.matrixV().col(comp);
        double sigma = svd.singularValues()(comp);

        Eigen::MatrixXd X_elem = sigma * U_col * V_col.transpose();

        // Diagonal averaging (anti-diagonals)
        PriceVec component(N, 0.0);
        std::vector<int> counts(N, 0);

        for (int i = 0; i < window_length; ++i) {
            for (int j = 0; j < K; ++j) {
                int idx = i + j;
                if (idx < N) {
                    component[idx] += X_elem(i, j);
                    counts[idx]++;
                }
            }
        }

        for (int i = 0; i < N; ++i) {
            if (counts[i] > 0) {
                component[i] /= counts[i];
            }
        }

        result.components[comp] = component;
    }

    // Trend = sum of first few components (low frequency)
    result.trend.resize(N, 0.0);
    int trend_comps = std::min(3, n_components);
    for (int i = 0; i < trend_comps; ++i) {
        for (int j = 0; j < N; ++j) {
            result.trend[j] += result.components[i][j];
        }
    }

    // Noise = residual
    result.noise.resize(N);
    for (int i = 0; i < N; ++i) {
        double reconstructed = 0.0;
        for (int c = 0; c < n_components; ++c) {
            reconstructed += result.components[c][i];
        }
        result.noise[i] = prices[i] - reconstructed;
    }

    return result;
}

} // namespace dominion::noise
