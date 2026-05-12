#include "ragd/dead_zone.h"
#include <nlohmann/json.hpp>
namespace ragd { std::string dead_zone_report_json(Storage &storage) { auto metrics = nlohmann::json::parse(storage.metrics_json()); return nlohmann::json{{"mode","basic"}, {"warnings", nlohmann::json::array()}, {"metrics", metrics}, {"note", "advanced dead-zone heuristics are deferred"}}.dump(); } }
