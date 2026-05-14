#include "dominion_native/agent_locks.hpp"

#include "dominion_native/path_normalizer.hpp"

#include <algorithm>

namespace dominion_native {
namespace {

bool compatible_modes(const std::string &existing, const std::string &requested) {
  if (existing == "exclusive" || requested == "exclusive") return false;
  if (existing == "write" || requested == "write") return false;
  return true;
}

}  // namespace

nlohmann::json LockDecision::to_json() const {
  return {{"acquired", acquired}, {"risk", risk}, {"reasons", reasons}};
}

LockDecision can_acquire_lock(const std::vector<AgentLock> &existing_locks, const AgentLock &requested, long long now_epoch) {
  LockDecision decision;
  decision.acquired = true;
  for (const auto &lock : existing_locks) {
    if (lock.status != "active") continue;
    if (lock.expires_at > 0 && now_epoch > 0 && lock.expires_at <= now_epoch) continue;
    if (lock.session_id == requested.session_id) continue;
    if (!path_has_parent_child_overlap(lock.path, requested.path)) continue;
    if (!compatible_modes(lock.mode, requested.mode)) {
      decision.acquired = false;
      decision.risk = (lock.mode == "exclusive" || requested.mode == "exclusive") ? "critical" : "high";
      decision.reasons.push_back("lock_conflict:" + lock.mode + "_vs_" + requested.mode);
    }
  }
  return decision;
}

}  // namespace dominion_native

