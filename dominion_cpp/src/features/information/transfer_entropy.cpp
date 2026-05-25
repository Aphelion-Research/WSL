#include "dominion/information.hpp"
#include <cmath>
#include <map>
#include <algorithm>

namespace dominion::information {

namespace {

int discretize(double value, double min_val, double max_val, int n_bins) {
    if (max_val - min_val < 1e-12) return 0;
    double normalized = (value - min_val) / (max_val - min_val);
    int bin = static_cast<int>(normalized * n_bins);
    return std::min(bin, n_bins - 1);
}

} // anonymous namespace

PriceVec compute_transfer_entropy(const PriceVec& source, const PriceVec& target, int n_bins, int lag, int window) {
    const int N = std::min(source.size(), target.size());
    PriceVec te(N, std::nan(""));

    for (int idx = window + lag; idx < N; ++idx) {
        std::map<std::tuple<int,int,int>, int> counts_xyz;
        std::map<std::tuple<int,int>, int> counts_xz;
        std::map<std::tuple<int,int>, int> counts_yz;
        std::map<int, int> counts_z;
        int total = 0;

        double src_min = *std::min_element(source.begin() + idx - window, source.begin() + idx);
        double src_max = *std::max_element(source.begin() + idx - window, source.begin() + idx);
        double tgt_min = *std::min_element(target.begin() + idx - window, target.begin() + idx);
        double tgt_max = *std::max_element(target.begin() + idx - window, target.begin() + idx);

        for (int i = idx - window + lag; i < idx; ++i) {
            int x = discretize(source[i - lag], src_min, src_max, n_bins);
            int y = discretize(target[i], tgt_min, tgt_max, n_bins);
            int z = discretize(target[i - 1], tgt_min, tgt_max, n_bins);

            counts_xyz[{x,y,z}]++;
            counts_xz[{x,z}]++;
            counts_yz[{y,z}]++;
            counts_z[z]++;
            total++;
        }

        double TE = 0.0;
        for (const auto& [key, count_xyz] : counts_xyz) {
            auto [x, y, z] = key;

            double p_xyz = static_cast<double>(count_xyz) / total;
            double p_xz = static_cast<double>(counts_xz[{x,z}]) / total;
            double p_yz = static_cast<double>(counts_yz[{y,z}]) / total;
            double p_z = static_cast<double>(counts_z[z]) / total;

            if (p_xyz > 0 && p_xz > 0 && p_yz > 0 && p_z > 0) {
                TE += p_xyz * std::log2((p_xyz * p_z) / (p_xz * p_yz));
            }
        }

        te[idx] = TE;
    }

    return te;
}

PriceVec compute_mutual_information(const PriceVec& x, const PriceVec& y, int n_bins, int window) {
    const int N = std::min(x.size(), y.size());
    PriceVec mi(N, std::nan(""));

    for (int idx = window; idx < N; ++idx) {
        std::map<std::pair<int,int>, int> counts_xy;
        std::map<int, int> counts_x, counts_y;
        int total = 0;

        double x_min = *std::min_element(x.begin() + idx - window, x.begin() + idx);
        double x_max = *std::max_element(x.begin() + idx - window, x.begin() + idx);
        double y_min = *std::min_element(y.begin() + idx - window, y.begin() + idx);
        double y_max = *std::max_element(y.begin() + idx - window, y.begin() + idx);

        for (int i = idx - window; i < idx; ++i) {
            int x_bin = discretize(x[i], x_min, x_max, n_bins);
            int y_bin = discretize(y[i], y_min, y_max, n_bins);

            counts_xy[{x_bin, y_bin}]++;
            counts_x[x_bin]++;
            counts_y[y_bin]++;
            total++;
        }

        double MI = 0.0;
        for (const auto& [key, count_xy] : counts_xy) {
            auto [x_bin, y_bin] = key;

            double p_xy = static_cast<double>(count_xy) / total;
            double p_x = static_cast<double>(counts_x[x_bin]) / total;
            double p_y = static_cast<double>(counts_y[y_bin]) / total;

            if (p_xy > 0 && p_x > 0 && p_y > 0) {
                MI += p_xy * std::log2(p_xy / (p_x * p_y));
            }
        }

        mi[idx] = MI;
    }

    return mi;
}

} // namespace dominion::information
