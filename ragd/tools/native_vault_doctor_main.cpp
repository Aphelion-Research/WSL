#include "dominion_native/vault_doctor.hpp"

#include <iostream>

namespace {
std::string value_after(int argc, char **argv, const std::string &flag, const std::string &fallback) {
  for (int i = 1; i + 1 < argc; ++i) {
    if (argv[i] == flag) return argv[i + 1];
  }
  return fallback;
}
}  // namespace

int main(int argc, char **argv) {
  try {
    const auto root = std::filesystem::absolute(value_after(argc, argv, "--root", ".")).lexically_normal();
    const auto vault = value_after(argc, argv, "--vault", (root / "vault").string());
    auto report = dominion_native::inspect_vault_native(root, vault);
    std::cout << report.to_json().dump(2) << "\n";
    return report.status == "fail" ? 1 : 0;
  } catch (const std::exception &exc) {
    std::cerr << "dominion-native-vault-doctor error: " << exc.what() << "\n";
    return 1;
  }
}

