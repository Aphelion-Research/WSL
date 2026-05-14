#include "dominion_native/agent_locks.hpp"

#include <cassert>

int main() {
  std::vector<dominion_native::AgentLock> locks = {{"src", "exclusive", "a", 0, "active"}};
  auto blocked = dominion_native::can_acquire_lock(locks, {"src/main.cpp", "write", "b", 0, "active"});
  assert(!blocked.acquired);
  auto same = dominion_native::can_acquire_lock(locks, {"src/main.cpp", "write", "a", 0, "active"});
  assert(same.acquired);
  std::vector<dominion_native::AgentLock> reads = {{"src/x.py", "read", "a", 0, "active"}};
  auto read_ok = dominion_native::can_acquire_lock(reads, {"src/x.py", "read", "b", 0, "active"});
  assert(read_ok.acquired);
  auto write_blocked = dominion_native::can_acquire_lock(reads, {"src/x.py", "write", "b", 0, "active"});
  assert(!write_blocked.acquired);
  return 0;
}

