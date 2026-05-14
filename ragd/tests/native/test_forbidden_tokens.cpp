#include "dominion_native/forbidden_tokens.hpp"

#include <cassert>
#include <filesystem>
#include <fstream>

int main() {
  auto dir = std::filesystem::temp_directory_path() / "dominion-native-forbidden-test";
  std::filesystem::remove_all(dir);
  std::filesystem::create_directories(dir / "config");
  std::filesystem::create_directories(dir / "src");
  std::ofstream(dir / "config" / "forbidden_tokens.json") << R"({
    "version": 1,
    "groups": {"x": ["danger_token"]},
    "allowlist_files": ["allowed.py"],
    "skip_parts": [".git", "__pycache__"]
  })";
  std::ofstream(dir / "src" / "bad.py") << "print('danger_' 'token')\n";
  std::ofstream(dir / "src" / "bad2.py") << "danger_token\n";
  auto policy = dominion_native::load_forbidden_policy(dir);
  auto findings = dominion_native::scan_forbidden_tokens(dir, policy);
  assert(findings.size() == 1);
  assert(findings[0].path == "src/bad2.py");
  return 0;
}

