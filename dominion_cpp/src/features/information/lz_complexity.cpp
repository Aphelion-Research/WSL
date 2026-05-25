#include "dominion/information.hpp"
#include <set>
#include <string>

namespace dominion::information {

PriceVec compute_lz_complexity(const PriceVec& prices, int window) {
    const int N = prices.size();
    PriceVec complexity(N, std::nan(""));

    for (int idx = window; idx < N; ++idx) {
        std::string binary;
        double median = 0.0;

        for (int i = idx - window; i < idx; ++i) {
            median += prices[i];
        }
        median /= window;

        for (int i = idx - window; i < idx; ++i) {
            binary += (prices[i] >= median) ? '1' : '0';
        }

        std::set<std::string> dictionary;
        std::string current = "";
        int c = 0;

        for (char bit : binary) {
            current += bit;
            if (dictionary.find(current) == dictionary.end()) {
                dictionary.insert(current);
                c++;
                current = "";
            }
        }

        complexity[idx] = static_cast<double>(c);
    }

    return complexity;
}

std::vector<ComplexityEntropyPoint> compute_complexity_entropy_plane(const PriceVec& prices, int embed_dim, int window) {
    std::vector<ComplexityEntropyPoint> points;

    PriceVec perm_entropy = compute_permutation_entropy(prices, embed_dim, 1, window);
    PriceVec lz_comp = compute_lz_complexity(prices, window);

    for (size_t i = 0; i < prices.size(); ++i) {
        if (!std::isnan(perm_entropy[i]) && !std::isnan(lz_comp[i])) {
            points.push_back({lz_comp[i], perm_entropy[i]});
        }
    }

    return points;
}

PriceVec compute_conditional_entropy(const PriceVec& x, const PriceVec& y, int n_bins, int window) {
    PriceVec mi = compute_mutual_information(x, y, n_bins, window);
    PriceVec h_y = compute_approximate_entropy(y, 2, 0.2, window);

    const int N = std::min(mi.size(), h_y.size());
    PriceVec cond_ent(N);

    for (int i = 0; i < N; ++i) {
        cond_ent[i] = h_y[i] - mi[i];
    }

    return cond_ent;
}

PriceVec compute_joint_entropy(const PriceVec& x, const PriceVec& y, int n_bins, int window) {
    const int N = std::min(x.size(), y.size());
    PriceVec joint_ent(N, std::nan(""));

    for (int idx = window; idx < N; ++idx) {
        std::map<std::pair<int,int>, int> counts_xy;
        int total = 0;

        double x_min = *std::min_element(x.begin() + idx - window, x.begin() + idx);
        double x_max = *std::max_element(x.begin() + idx - window, x.begin() + idx);
        double y_min = *std::min_element(y.begin() + idx - window, y.begin() + idx);
        double y_max = *std::max_element(y.begin() + idx - window, y.begin() + idx);

        for (int i = idx - window; i < idx; ++i) {
            int x_bin = (x_max - x_min < 1e-12) ? 0 : std::min(static_cast<int>((x[i] - x_min) / (x_max - x_min) * n_bins), n_bins - 1);
            int y_bin = (y_max - y_min < 1e-12) ? 0 : std::min(static_cast<int>((y[i] - y_min) / (y_max - y_min) * n_bins), n_bins - 1);

            counts_xy[{x_bin, y_bin}]++;
            total++;
        }

        double H = 0.0;
        for (const auto& [key, count] : counts_xy) {
            double p = static_cast<double>(count) / total;
            if (p > 0) {
                H -= p * std::log2(p);
            }
        }

        joint_ent[idx] = H;
    }

    return joint_ent;
}

PriceVec compute_kl_divergence(const PriceVec& p_series, const PriceVec& q_series, int n_bins, int window) {
    const int N = std::min(p_series.size(), q_series.size());
    PriceVec kl(N, std::nan(""));

    for (int idx = window; idx < N; ++idx) {
        std::vector<double> p_hist(n_bins, 0.0), q_hist(n_bins, 0.0);

        double p_min = *std::min_element(p_series.begin() + idx - window, p_series.begin() + idx);
        double p_max = *std::max_element(p_series.begin() + idx - window, p_series.begin() + idx);
        double q_min = *std::min_element(q_series.begin() + idx - window, q_series.begin() + idx);
        double q_max = *std::max_element(q_series.begin() + idx - window, q_series.begin() + idx);

        for (int i = idx - window; i < idx; ++i) {
            int p_bin = (p_max - p_min < 1e-12) ? 0 : std::min(static_cast<int>((p_series[i] - p_min) / (p_max - p_min) * n_bins), n_bins - 1);
            int q_bin = (q_max - q_min < 1e-12) ? 0 : std::min(static_cast<int>((q_series[i] - q_min) / (q_max - q_min) * n_bins), n_bins - 1);

            p_hist[p_bin]++;
            q_hist[q_bin]++;
        }

        double KL = 0.0;
        for (int b = 0; b < n_bins; ++b) {
            double p = (p_hist[b] + 1e-10) / window;
            double q = (q_hist[b] + 1e-10) / window;
            KL += p * std::log2(p / q);
        }

        kl[idx] = KL;
    }

    return kl;
}

} // namespace dominion::information
