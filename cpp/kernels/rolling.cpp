#include "rolling.hpp"

namespace hydra {

constexpr float NAN_F = std::numeric_limits<float>::quiet_NaN();

std::vector<float> rolling_mean(const std::vector<float>& data, int window) {
    std::vector<float> result(data.size(), NAN_F);

    for (size_t i = window - 1; i < data.size(); ++i) {
        double sum = 0.0;
        int count = 0;

        for (int j = 0; j < window; ++j) {
            float val = data[i - j];
            if (!std::isnan(val)) {
                sum += val;
                ++count;
            }
        }

        result[i] = count > 0 ? static_cast<float>(sum / count) : NAN_F;
    }

    return result;
}

std::vector<float> rolling_std(const std::vector<float>& data, int window) {
    std::vector<float> result(data.size(), NAN_F);

    for (size_t i = window - 1; i < data.size(); ++i) {
        double sum = 0.0;
        double sum_sq = 0.0;
        int count = 0;

        for (int j = 0; j < window; ++j) {
            float val = data[i - j];
            if (!std::isnan(val)) {
                sum += val;
                sum_sq += val * val;
                ++count;
            }
        }

        if (count > 1) {
            double mean = sum / count;
            double variance = (sum_sq / count) - (mean * mean);
            result[i] = variance > 0 ? static_cast<float>(std::sqrt(variance)) : 0.0f;
        }
    }

    return result;
}

std::vector<float> rolling_min(const std::vector<float>& data, int window) {
    std::vector<float> result(data.size(), NAN_F);

    for (size_t i = window - 1; i < data.size(); ++i) {
        float min_val = std::numeric_limits<float>::max();
        bool found = false;

        for (int j = 0; j < window; ++j) {
            float val = data[i - j];
            if (!std::isnan(val)) {
                min_val = std::min(min_val, val);
                found = true;
            }
        }

        result[i] = found ? min_val : NAN_F;
    }

    return result;
}

std::vector<float> rolling_max(const std::vector<float>& data, int window) {
    std::vector<float> result(data.size(), NAN_F);

    for (size_t i = window - 1; i < data.size(); ++i) {
        float max_val = std::numeric_limits<float>::lowest();
        bool found = false;

        for (int j = 0; j < window; ++j) {
            float val = data[i - j];
            if (!std::isnan(val)) {
                max_val = std::max(max_val, val);
                found = true;
            }
        }

        result[i] = found ? max_val : NAN_F;
    }

    return result;
}

std::vector<float> rolling_zscore(const std::vector<float>& data, int window) {
    std::vector<float> result(data.size(), NAN_F);

    for (size_t i = window - 1; i < data.size(); ++i) {
        double sum = 0.0;
        double sum_sq = 0.0;
        int count = 0;

        for (int j = 0; j < window; ++j) {
            float val = data[i - j];
            if (!std::isnan(val)) {
                sum += val;
                sum_sq += val * val;
                ++count;
            }
        }

        if (count > 1 && !std::isnan(data[i])) {
            double mean = sum / count;
            double variance = (sum_sq / count) - (mean * mean);
            if (variance > 0) {
                double std = std::sqrt(variance);
                result[i] = static_cast<float>((data[i] - mean) / std);
            }
        }
    }

    return result;
}

std::vector<float> rolling_skew(const std::vector<float>& data, int window) {
    std::vector<float> result(data.size(), NAN_F);

    for (size_t i = window - 1; i < data.size(); ++i) {
        std::vector<double> vals;
        vals.reserve(window);

        for (int j = 0; j < window; ++j) {
            float val = data[i - j];
            if (!std::isnan(val)) {
                vals.push_back(val);
            }
        }

        if (vals.size() > 2) {
            double mean = std::accumulate(vals.begin(), vals.end(), 0.0) / vals.size();
            double m2 = 0.0, m3 = 0.0;

            for (double v : vals) {
                double diff = v - mean;
                m2 += diff * diff;
                m3 += diff * diff * diff;
            }

            m2 /= vals.size();
            m3 /= vals.size();

            if (m2 > 0) {
                result[i] = static_cast<float>(m3 / std::pow(m2, 1.5));
            }
        }
    }

    return result;
}

std::vector<float> rolling_kurt(const std::vector<float>& data, int window) {
    std::vector<float> result(data.size(), NAN_F);

    for (size_t i = window - 1; i < data.size(); ++i) {
        std::vector<double> vals;
        vals.reserve(window);

        for (int j = 0; j < window; ++j) {
            float val = data[i - j];
            if (!std::isnan(val)) {
                vals.push_back(val);
            }
        }

        if (vals.size() > 3) {
            double mean = std::accumulate(vals.begin(), vals.end(), 0.0) / vals.size();
            double m2 = 0.0, m4 = 0.0;

            for (double v : vals) {
                double diff = v - mean;
                double diff2 = diff * diff;
                m2 += diff2;
                m4 += diff2 * diff2;
            }

            m2 /= vals.size();
            m4 /= vals.size();

            if (m2 > 0) {
                result[i] = static_cast<float>(m4 / (m2 * m2) - 3.0);  // Excess kurtosis
            }
        }
    }

    return result;
}

std::vector<float> rolling_corr(const std::vector<float>& x,
                                const std::vector<float>& y,
                                int window) {
    if (x.size() != y.size()) {
        return std::vector<float>(x.size(), NAN_F);
    }

    std::vector<float> result(x.size(), NAN_F);

    for (size_t i = window - 1; i < x.size(); ++i) {
        double sum_x = 0.0, sum_y = 0.0;
        double sum_x2 = 0.0, sum_y2 = 0.0, sum_xy = 0.0;
        int count = 0;

        for (int j = 0; j < window; ++j) {
            float vx = x[i - j];
            float vy = y[i - j];

            if (!std::isnan(vx) && !std::isnan(vy)) {
                sum_x += vx;
                sum_y += vy;
                sum_x2 += vx * vx;
                sum_y2 += vy * vy;
                sum_xy += vx * vy;
                ++count;
            }
        }

        if (count > 1) {
            double n = static_cast<double>(count);
            double num = n * sum_xy - sum_x * sum_y;
            double den_x = n * sum_x2 - sum_x * sum_x;
            double den_y = n * sum_y2 - sum_y * sum_y;

            if (den_x > 0 && den_y > 0) {
                result[i] = static_cast<float>(num / std::sqrt(den_x * den_y));
            }
        }
    }

    return result;
}

} // namespace hydra
