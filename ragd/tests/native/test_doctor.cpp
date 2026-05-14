#include "dominion_native/doctor.hpp"

#include <cassert>

int main() {
  dominion_native::DoctorOptions options;
  options.root = DOMINION_SOURCE_ROOT;
  options.offline = true;
  options.live = false;
  auto report = dominion_native::run_native_doctor(options);
  auto json = report.to_json();
  assert(json.contains("checks"));
  assert(json["checks"].contains("ignore_rules"));
  assert(json["checks"].contains("ragd_reachable"));
  assert(json["checks"]["ragd_reachable"]["status"] == "skip");
  assert(report.exit_code(false) == 0 || report.to_json()["overall"] == "fail");
  return 0;
}

