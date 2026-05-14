#pragma once

#include <filesystem>
#include <nlohmann/json.hpp>
#include <string>
#include <vector>

namespace dominion_native {

struct ForbiddenPolicy {
  std::vector<std::string> tokens;
  std::vector<std::string> allowlist_files;
  std::vector<std::string> skip_parts;
  std::string fingerprint;
};

struct ForbiddenFinding {
  std::string path;
  std::string token;

  nlohmann::json to_json() const;
};

ForbiddenPolicy load_forbidden_policy(const std::filesystem::path &repo_root);
std::vector<ForbiddenFinding> scan_forbidden_tokens(const std::filesystem::path &root, const ForbiddenPolicy &policy);

}  // namespace dominion_native

