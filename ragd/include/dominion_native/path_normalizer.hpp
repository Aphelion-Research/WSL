#pragma once

#include <filesystem>
#include <nlohmann/json.hpp>
#include <string>

namespace dominion_native {

struct NormalizedPath {
  std::string absolute;
  std::string repo_root;
  std::string relative;
  std::string display;
  bool exists = false;
  bool is_symlink = false;
  std::string realpath;
  bool within_repo = false;
  bool windows_style = false;
  bool wine_path = false;
  std::string error;

  nlohmann::json to_json() const;
};

NormalizedPath normalize_path(const std::filesystem::path &repo_root, const std::filesystem::path &candidate_path);
std::string slash_path(const std::filesystem::path &path);
bool path_has_parent_child_overlap(const std::string &a, const std::string &b);

}  // namespace dominion_native

