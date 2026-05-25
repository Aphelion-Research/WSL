#include <cmath>
#include "dominion/features.hpp"
#include <ctime>
#include <sstream>

namespace dominion::features {

FeatureMap compute_calendar_features(const std::vector<Timestamp>& timestamps,
                                     const std::vector<std::string>& fomc_dates) {
    FeatureMap features;
    if (timestamps.empty()) return features;

    std::vector<PriceVec> dow_vectors(5, PriceVec(timestamps.size(), 0.0));
    std::vector<PriceVec> month_vectors(12, PriceVec(timestamps.size(), 0.0));
    std::vector<PriceVec> quarter_vectors(4, PriceVec(timestamps.size(), 0.0));

    PriceVec week_of_month(timestamps.size());
    PriceVec month_end_flag(timestamps.size());
    PriceVec quarter_end_flag(timestamps.size());
    PriceVec days_to_options_expiry(timestamps.size());
    PriceVec days_to_fomc(timestamps.size());
    PriceVec seasonal_q4(timestamps.size());
    PriceVec seasonal_ramadan(timestamps.size());

    std::vector<Timestamp> fomc_timestamps;
    for (const auto& date_str : fomc_dates) {
        std::tm tm = {};
        std::istringstream ss(date_str);
        ss >> std::get_time(&tm, "%Y-%m-%d");
        fomc_timestamps.push_back(std::chrono::system_clock::from_time_t(std::mktime(&tm)));
    }

    for (size_t i = 0; i < timestamps.size(); ++i) {
        auto t = std::chrono::system_clock::to_time_t(timestamps[i]);
        std::tm* tm = std::gmtime(&t);

        int dow = tm->tm_wday;
        if (dow >= 1 && dow <= 5) dow_vectors[dow - 1][i] = 1.0;

        week_of_month[i] = (tm->tm_mday - 1) / 7 + 1;

        int days_in_month = 31;
        if (tm->tm_mon == 1) days_in_month = 28;
        if (tm->tm_mon == 3 || tm->tm_mon == 5 || tm->tm_mon == 8 || tm->tm_mon == 10) days_in_month = 30;
        month_end_flag[i] = (tm->tm_mday >= days_in_month - 4) ? 1.0 : 0.0;

        int month = tm->tm_mon + 1;
        bool is_qtr_end = (month == 3 || month == 6 || month == 9 || month == 12);
        quarter_end_flag[i] = (is_qtr_end && tm->tm_mday >= 25) ? 1.0 : 0.0;

        month_vectors[tm->tm_mon][i] = 1.0;
        quarter_vectors[tm->tm_mon / 3][i] = 1.0;

        std::tm first = *tm;
        first.tm_mday = 1;
        std::mktime(&first);
        int first_dow = first.tm_wday;
        int third_friday = 15 + ((5 - first_dow + 7) % 7);
        if (third_friday > 21) third_friday -= 7;
        days_to_options_expiry[i] = third_friday - tm->tm_mday;
        if (days_to_options_expiry[i] < 0) days_to_options_expiry[i] += 30;

        double min_days = 365.0;
        for (const auto& fomc_ts : fomc_timestamps) {
            auto diff = std::chrono::duration_cast<std::chrono::hours>(fomc_ts - timestamps[i]);
            double days_diff = diff.count() / 24.0;
            if (days_diff >= 0 && days_diff < min_days) min_days = days_diff;
        }
        days_to_fomc[i] = min_days;

        seasonal_q4[i] = (month >= 10 && month <= 12) ? 1.0 : 0.0;
        seasonal_ramadan[i] = (month >= 3 && month <= 4) ? 1.0 : 0.0;
    }

    for (int d = 0; d < 5; ++d) {
        std::string day_names[] = {"Mon", "Tue", "Wed", "Thu", "Fri"};
        features["day_of_week_" + day_names[d]] = dow_vectors[d];
    }

    for (int m = 0; m < 12; ++m) {
        features["month_" + std::to_string(m + 1)] = month_vectors[m];
    }

    for (int q = 0; q < 4; ++q) {
        features["quarter_" + std::to_string(q + 1)] = quarter_vectors[q];
    }

    features["week_of_month"] = week_of_month;
    features["month_end_flag"] = month_end_flag;
    features["quarter_end_flag"] = quarter_end_flag;
    features["days_to_options_expiry"] = days_to_options_expiry;
    features["days_to_fomc"] = days_to_fomc;
    features["seasonal_q4"] = seasonal_q4;
    features["seasonal_ramadan"] = seasonal_ramadan;

    return features;
}

} // namespace dominion::features
