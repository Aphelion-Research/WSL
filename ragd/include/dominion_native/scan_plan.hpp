#pragma once

#include "dominion_native/file_classifier.hpp"
#include "dominion_native/ignore_policy.hpp"

#include <filesystem>
#include <nlohmann/json.hpp>
#include <string>
#include <vector>

namespace dominion_native {

struct ScanFile {
  std::string relative_path;
  std::string absolute_path;
  std::string language;
  std::string kind;
  std::string content_hash;
  std::uintmax_t size_bytes = 0;
  long long mtime_ns = 0;

  nlohmann::json to_json() const;
};

struct ScanError {
  std::string path;
  std::string code;
  std::string message;

  nlohmann::json to_json() const;
};

struct ScanPlanOptions {
  std::size_t max_files = 0;
  std::uintmax_t max_bytes = 0;
  bool strict = false;
  bool include_files = true;
  bool include_ignored = false;
};

struct ScanPlan {
  std::string root;
  std::string policy_fingerprint;
  std::vector<ScanFile> files;
  std::vector<IgnoreDecision> ignored;
  std::vector<ScanError> errors;
  std::uintmax_t bytes_included = 0;
  std::size_t seen = 0;

  std::string plan_hash() const;
  nlohmann::json to_json(bool include_files = true, bool include_ignored = false) const;
};

ScanPlan build_scan_plan(const std::filesystem::path &repo_root, const ScanPlanOptions &options = {});

}  // namespace dominion_native

