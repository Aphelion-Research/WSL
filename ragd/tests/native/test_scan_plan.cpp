#include "dominion_native/scan_plan.hpp"

#include <cassert>
#include <filesystem>
#include <fstream>

int main() {
  auto dir = std::filesystem::temp_directory_path() / "dominion-native-scan-test";
  std::filesystem::remove_all(dir);
  std::filesystem::create_directories(dir / "src");
  std::filesystem::create_directories(dir / "secrets");
  std::ofstream(dir / "src" / "main.cpp") << "int main(){}\n";
  std::ofstream(dir / "secrets" / "fake.env") << "SECRET_VALUE_SHOULD_NOT_APPEAR\n";
  dominion_native::ScanPlanOptions options;
  options.include_ignored = true;
  auto plan = dominion_native::build_scan_plan(dir, options);
  assert(plan.files.size() == 1);
  assert(plan.files[0].relative_path == "src/main.cpp");
  assert(!plan.files[0].content_hash.empty());
  bool saw_secret_ignored = false;
  for (const auto &ignored : plan.ignored) {
    if (ignored.path == "secrets") saw_secret_ignored = ignored.secret_protected;
  }
  assert(saw_secret_ignored);
  auto dumped = plan.to_json(true, true).dump();
  assert(dumped.find("SECRET_VALUE_SHOULD_NOT_APPEAR") == std::string::npos);
  assert(plan.plan_hash().rfind("sha256:", 0) == 0);
  return 0;
}

