#include "ragd/temporal.h"
#include <nlohmann/json.hpp>
namespace ragd { std::string temporal_status_json() { return nlohmann::json{{"enabled", false}, {"reason", "temporal git indexing is deferred in the MVP"}}.dump(); } }
