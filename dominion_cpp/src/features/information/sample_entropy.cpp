#include "dominion/information.hpp"
#include <cmath>
#include <algorithm>

namespace dominion::information {

PriceVec compute_sample_entropy(const PriceVec& prices, int m, double r, int window) {
    const int N = prices.size();
    PriceVec entropy(N, std::nan(""));

    for (int idx = window; idx < N; ++idx) {
        int B = 0, A = 0;

        for (int i = idx - window; i < idx - m; ++i) {
            for (int j = i + 1; j < idx - m + 1; ++j) {
                bool match_m = true, match_m1 = true;

                for (int k = 0; k < m && match_m; ++k) {
                    if (std::abs(prices[i + k] - prices[j + k]) > r) {
                        match_m = false;
                    }
                }

                if (match_m) {
                    B++;
                    if (std::abs(prices[i + m] - prices[j + m]) <= r) {
                        A++;
                    }
                }
            }
        }

        if (B > 0 && A > 0) {
            entropy[idx] = -std::log(static_cast<double>(A) / B);
        }
    }

    return entropy;
}

PriceVec compute_approximate_entropy(const PriceVec& prices, int m, double r, int window) {
    const int N = prices.size();
    PriceVec entropy(N, std::nan(""));

    for (int idx = window; idx < N; ++idx) {
        double phi_m = 0.0, phi_m1 = 0.0;

        for (int i = idx - window; i < idx - m; ++i) {
            int count_m = 0, count_m1 = 0;

            for (int j = idx - window; j < idx - m; ++j) {
                bool match_m = true, match_m1 = true;

                for (int k = 0; k < m && match_m; ++k) {
                    if (std::abs(prices[i + k] - prices[j + k]) > r) {
                        match_m = false;
                    }
                }

                if (match_m) {
                    count_m++;
                    for (int k = 0; k <= m && match_m1; ++k) {
                        if (std::abs(prices[i + k] - prices[j + k]) > r) {
                            match_m1 = false;
                        }
                    }
                    if (match_m1) {
                        count_m1++;
                    }
                }
            }

            if (count_m > 0) {
                phi_m += std::log(static_cast<double>(count_m) / (idx - window - m + 1));
            }
            if (count_m1 > 0) {
                phi_m1 += std::log(static_cast<double>(count_m1) / (idx - window - m));
            }
        }

        entropy[idx] = (phi_m - phi_m1) / (idx - window - m + 1);
    }

    return entropy;
}

} // namespace dominion::information
