#pragma once

#include <nlohmann/json.hpp>
#include <string>
#include <vector>

namespace dominion_native {

struct AgentLock {
  std::string path;
  std::string mode;
  std::string session_id;
  long long expires_at = 0;
  std::string status = "active";
};

struct LockDecision {
  bool acquired = false;
  std::string risk = "none";
  std::vector<std::string> reasons;

  nlohmann::json to_json() const;
};

LockDecision can_acquire_lock(const std::vector<AgentLock> &existing_locks, const AgentLock &requested, long long now_epoch = 0);

}  // namespace dominion_native

