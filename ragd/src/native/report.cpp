#include "dominion_native/report.hpp"

#include <iostream>

namespace dominion_native {

void print_json_or_human(const nlohmann::json &payload, bool json_mode, const std::string &human_summary) {
  if (json_mode) {
    std::cout << payload.dump(2) << "\n";
  } else {
    std::cout << human_summary << "\n";
  }
}

}  // namespace dominion_native

