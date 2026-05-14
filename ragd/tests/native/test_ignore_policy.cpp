#include "dominion_native/ignore_policy.hpp"

#include <cassert>
#include <filesystem>

int main() {
  auto policy = dominion_native::default_ignore_policy();
  auto secret = policy.decide("secrets/fake.env", false, 4);
  assert(secret.ignored);
  assert(secret.secret_protected);
  assert(secret.reason == "secret_protected");
  assert(policy.decide(".git/config", false, 4).ignored);
  assert(policy.decide("data/raw/tick.csv", false, 4).ignored);
  assert(policy.decide("src/main.cpp", false, 4).ignored == false);
  assert(!policy.fingerprint().empty());
  auto loaded = dominion_native::load_ignore_policy(DOMINION_SOURCE_ROOT);
  assert(loaded.decide("secrets/fake.env", false, 4).secret_protected);
  assert(loaded.fingerprint() == "b119281bacdd81fab510139234c9a4ac9d3c9e1866e769e7bfc1dd76a2a8fc00");
  return 0;
}

