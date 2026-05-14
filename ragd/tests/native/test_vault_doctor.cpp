#include "dominion_native/vault_doctor.hpp"

#include <cassert>
#include <filesystem>
#include <fstream>

int main() {
  auto dir = std::filesystem::temp_directory_path() / "dominion-native-vault-test";
  std::filesystem::remove_all(dir);
  std::filesystem::create_directories(dir / "vault");
  std::ofstream(dir / "vault" / "note.md") << "[stale](/tmp/pytest-of-Martin/foo/bar.py)\n[missing](missing.md)\n";
  auto report = dominion_native::inspect_vault_native(dir, dir / "vault");
  assert(!report.ok);
  assert(report.broken_links >= 2);
  assert(report.stale_links >= 1);
  assert(!report.examples.empty());
  return 0;
}

