#include "dominion_native/manifest_store.hpp"

#include <cassert>
#include <filesystem>
#include <fstream>

int main() {
  auto dir = std::filesystem::temp_directory_path() / "dominion-native-manifest-test";
  std::filesystem::remove_all(dir);
  std::filesystem::create_directories(dir / "src");
  auto db = dir / "manifest.db";
  std::ofstream(dir / "src" / "a.cpp") << "int a() { return 1; }\n";
  auto first = dominion_native::manifest_scan_json(db, dir);
  assert(first["summary"]["included"] == 1);
  auto doctor1 = dominion_native::manifest_doctor_json(db);
  assert(doctor1["ok"] == true);
  std::ofstream(dir / "src" / "a.cpp") << "int a() { return 2; }\n";
  auto second = dominion_native::manifest_scan_json(db, dir);
  assert(second["summary"]["included"] == 1);
  std::filesystem::remove(dir / "src" / "a.cpp");
  auto third = dominion_native::manifest_scan_json(db, dir);
  assert(third["summary"]["included"] == 0);
  auto doctor2 = dominion_native::manifest_doctor_json(db);
  assert(doctor2["ok"] == true);
  return 0;
}

