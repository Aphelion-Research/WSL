#include "dominion_native/manifest_store.hpp"
#include "dominion_native/scan_plan.hpp"
#include "dominion_native/version.hpp"

#include <chrono>
#include <iostream>

namespace {
std::string value_after(int argc, char **argv, const std::string &flag, const std::string &fallback) {
  for (int i = 1; i + 1 < argc; ++i) {
    if (argv[i] == flag) return argv[i + 1];
  }
  return fallback;
}
bool has_flag(int argc, char **argv, const std::string &flag) {
  for (int i = 1; i < argc; ++i) {
    if (argv[i] == flag) return true;
  }
  return false;
}
}  // namespace

int main(int argc, char **argv) {
  try {
    const std::string command = argc > 1 ? argv[1] : "help";
    if (command == "bench") {
      const auto root = value_after(argc, argv, "--root", ".");
      auto started = std::chrono::steady_clock::now();
      auto plan = dominion_native::build_scan_plan(root);
      auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - started).count();
      double seconds = elapsed > 0 ? static_cast<double>(elapsed) / 1000.0 : 0.001;
      double mb = static_cast<double>(plan.bytes_included) / (1024.0 * 1024.0);
      nlohmann::json payload = {
          {"bench_id", plan.plan_hash().substr(7, 16)},
          {"root", plan.root},
          {"native_core_version", dominion_native::kNativeCoreVersion},
          {"metrics", {
              {"scan_files_per_sec", static_cast<double>(plan.files.size()) / seconds},
              {"hash_mb_per_sec", mb / seconds},
              {"cold_scan_wall_ms", elapsed},
          }},
          {"summary", plan.to_json(false, false)["summary"]},
      };
      std::cout << payload.dump(2) << "\n";
      return 0;
    }
    if (command == "scan") {
      auto plan = dominion_native::build_scan_plan(value_after(argc, argv, "--root", "."));
      std::cout << plan.to_json(true, has_flag(argc, argv, "--include-ignored")).dump(2) << "\n";
      return plan.errors.empty() ? 0 : 1;
    }
    std::cout << "dominion-native " << dominion_native::kNativeCoreVersion << "\n";
    std::cout << "commands: bench, scan\n";
    return command == "help" ? 0 : 2;
  } catch (const std::exception &exc) {
    std::cerr << "dominion-native error: " << exc.what() << "\n";
    return 1;
  }
}

