#pragma once

#include <nlohmann/json.hpp>
#include <string>

namespace dominion_native {

void print_json_or_human(const nlohmann::json &payload, bool json_mode, const std::string &human_summary);

}  // namespace dominion_native

