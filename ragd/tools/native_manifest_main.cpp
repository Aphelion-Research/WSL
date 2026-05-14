#include "dominion_native/manifest_store.hpp"

#include <cstdlib>
#include <filesystem>
#include <iostream>

namespace {
std::string value_after(int argc, char **argv, const std::string &flag, const std::string &fallback) {
  for (int i = 1; i + 1 < argc; ++i) {
    if (argv[i] == flag) return argv[i + 1];
  }
  return fallback;
}
std::filesystem::path expand_user(std::string value) {
  if (value.rfind("~/", 0) == 0) {
    const char *home = std::getenv("HOME");
    if (home) return std::filesystem::path(home) / value.substr(2);
  }
  return value;
}
}  // namespace

int main(int argc, char **argv) {
  if (argc < 2) {
    std::cerr << "usage: dominion-native-manifest init|scan|doctor --db PATH [--root PATH] [--json]\n";
    return 2;
  }
  try {
    const std::string command = argv[1];
    const auto db = expand_user(value_after(argc, argv, "--db", "~/.dominion/native_manifest.db"));
    nlohmann::json payload;
    if (command == "init") {
      payload = dominion_native::manifest_init_json(db);
    } else if (command == "scan") {
      payload = dominion_native::manifest_scan_json(db, value_after(argc, argv, "--root", "."));
    } else if (command == "doctor") {
      payload = dominion_native::manifest_doctor_json(db);
    } else {
      std::cerr << "unknown manifest command: " << command << "\n";
      return 2;
    }
    std::cout << payload.dump(2) << "\n";
    return payload.value("ok", true) ? 0 : 1;
  } catch (const std::exception &exc) {
    std::cerr << "dominion-native-manifest error: " << exc.what() << "\n";
    return 1;
  }
}

