#pragma once

#include <filesystem>
#include <nlohmann/json.hpp>
#include <regex>
#include <string>
#include <vector>

namespace dominion_native {

struct IgnoreDecision {
  std::string path;
  bool ignored = false;
  std::string reason;
  std::string rule_id;
  bool secret_protected = false;
  std::string source = "builtin";

  nlohmann::json to_json() const;
};

struct IgnorePolicy {
  int version = 1;
  std::vector<std::string> dir_deny;
  std::vector<std::string> ext_deny;
  std::vector<std::string> path_deny;
  std::size_t max_bytes = 512 * 1024;
  bool secrets_always_ignored = true;
  std::string source = "builtin";
  std::string config_hash;

  IgnoreDecision decide(const std::filesystem::path &relative_path, bool is_directory = false, std::uintmax_t size_bytes = 0) const;
  nlohmann::json policy_json() const;
  std::string fingerprint() const;
};

IgnorePolicy default_ignore_policy();
IgnorePolicy load_ignore_policy(const std::filesystem::path &repo_root);

}  // namespace dominion_native

