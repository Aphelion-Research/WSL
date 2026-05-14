#include "dominion_native/scan_plan.hpp"

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
    dominion_native::ScanPlanOptions options;
    options.strict = has_flag(argc, argv, "--strict");
    options.include_files = true;
    options.include_ignored = has_flag(argc, argv, "--include-ignored");
    const auto root = value_after(argc, argv, "--root", ".");
    const auto max_files = value_after(argc, argv, "--max-files", "");
    const auto max_bytes = value_after(argc, argv, "--max-bytes", "");
    if (!max_files.empty()) options.max_files = static_cast<std::size_t>(std::stoull(max_files));
    if (!max_bytes.empty()) options.max_bytes = static_cast<std::uintmax_t>(std::stoull(max_bytes));
    auto plan = dominion_native::build_scan_plan(root, options);
    if (has_flag(argc, argv, "--json")) {
      std::cout << plan.to_json(options.include_files, options.include_ignored).dump(2) << "\n";
    } else {
      std::cout << "Dominion native scan: included=" << plan.files.size() << " ignored=" << plan.ignored.size() << " errors=" << plan.errors.size() << "\n";
    }
    return (options.strict && !plan.errors.empty()) ? 1 : 0;
  } catch (const std::exception &exc) {
    std::cerr << "dominion-native-scan error: " << exc.what() << "\n";
    return 1;
  }
}

