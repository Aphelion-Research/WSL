#include "dominion_native/doctor.hpp"

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
    dominion_native::DoctorOptions options;
    options.root = value_after(argc, argv, "--root", ".");
    options.live = has_flag(argc, argv, "--live");
    options.offline = has_flag(argc, argv, "--offline") || !options.live;
    options.strict = has_flag(argc, argv, "--strict");
    auto report = dominion_native::run_native_doctor(options);
    if (has_flag(argc, argv, "--json")) {
      std::cout << report.to_json().dump(2) << "\n";
    } else {
      std::cout << "Dominion native doctor: " << report.to_json().value("overall", "unknown") << "\n";
      for (const auto &check : report.checks) std::cout << "  " << check.status << " " << check.name << ": " << check.message << "\n";
    }
    return report.exit_code(options.strict);
  } catch (const std::exception &exc) {
    std::cerr << "dominion-native-doctor error: " << exc.what() << "\n";
    return 1;
  }
}

