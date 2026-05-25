#include "dominion/features.hpp"

namespace dominion::features {

FeatureMap compute_calendar_features(const std::vector<Timestamp>& timestamps,
                                     const std::vector<std::string>& fomc_dates) {
    FeatureMap features;

    // TODO: Day of week, week of month, month, quarter, month-end, quarter-end,
    // days to options expiry, seasonal (Q4, Ramadan)

    return features;
}

} // namespace dominion::features
