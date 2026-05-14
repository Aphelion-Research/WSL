#pragma once

#include <nlohmann/json.hpp>
#include <string>
#include <vector>

namespace dominion_native {

struct TaskScope {
  std::vector<std::string> paths;
  std::vector<std::string> symbols;
  std::vector<std::string> packages;
};

struct ScopeOverlap {
  bool overlap = false;
  std::string risk = "none";
  std::vector<std::string> reasons;

  nlohmann::json to_json() const;
};

ScopeOverlap analyze_scope_overlap(const TaskScope &a, const TaskScope &b);
nlohmann::json validate_completion_evidence(const nlohmann::json &claim);

}  // namespace dominion_native

