#include "dominion_native/path_normalizer.hpp"

#include <cassert>
#include <filesystem>
#include <fstream>

int main() {
  auto dir = std::filesystem::temp_directory_path() / "dominion-native-path-test";
  std::filesystem::remove_all(dir);
  std::filesystem::create_directories(dir / "src");
  std::ofstream(dir / "src" / "main.cpp") << "int main(){}\n";
  auto normal = dominion_native::normalize_path(dir, "src/../src/main.cpp");
  assert(normal.within_repo);
  assert(normal.relative == "src/main.cpp");
  auto missing = dominion_native::normalize_path(dir, "src/missing.cpp");
  assert(missing.within_repo);
  assert(!missing.exists);
  auto outside = dominion_native::normalize_path(dir, "../outside.cpp");
  assert(!outside.within_repo);
  auto win = dominion_native::normalize_path(dir, "C:\\Users\\x\\file.cpp");
  assert(win.windows_style);
  assert(!win.within_repo);
  auto wine = dominion_native::normalize_path(dir, "drive_c/users/x/file.txt");
  assert(wine.wine_path);
  assert(dominion_native::path_has_parent_child_overlap("ragd/src", "ragd/src/main.cpp"));
  return 0;
}

