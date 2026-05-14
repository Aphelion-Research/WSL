#include "dominion_native/scan_plan.hpp"

#include "dominion_native/content_hash.hpp"
#include "dominion_native/path_normalizer.hpp"

#include <algorithm>
#include <sys/stat.h>

namespace dominion_native {
namespace {

long long mtime_ns_for(const std::filesystem::path &path) {
  struct stat st {};
  if (::stat(path.c_str(), &st) != 0) return 0;
#if defined(st_mtim)
  return static_cast<long long>(st.st_mtim.tv_sec) * 1000000000LL + st.st_mtim.tv_nsec;
#else
  return static_cast<long long>(st.st_mtime) * 1000000000LL;
#endif
}

std::string safe_relative(const std::filesystem::path &root, const std::filesystem::path &path) {
  std::error_code ec;
  auto rel = std::filesystem::relative(path, root, ec);
  if (ec) rel = path.lexically_relative(root);
  return slash_path(rel);
}

}  // namespace

nlohmann::json ScanFile::to_json() const {
  return {
      {"relative_path", relative_path},
      {"absolute_path", absolute_path},
      {"language", language},
      {"kind", kind},
      {"content_hash", content_hash},
      {"size_bytes", size_bytes},
      {"mtime_ns", mtime_ns},
  };
}

nlohmann::json ScanError::to_json() const {
  return {{"path", path}, {"code", code}, {"message", message}};
}

std::string ScanPlan::plan_hash() const {
  nlohmann::json files_json = nlohmann::json::array();
  for (const auto &file : files) {
    files_json.push_back({{"path", file.relative_path}, {"hash", file.content_hash}, {"size", file.size_bytes}});
  }
  return "sha256:" + sha256_string(nlohmann::json{{"policy", policy_fingerprint}, {"files", files_json}}.dump());
}

nlohmann::json ScanPlan::to_json(bool include_files_value, bool include_ignored_value) const {
  nlohmann::json summary = {
      {"seen", seen},
      {"included", files.size()},
      {"ignored", ignored.size()},
      {"errors", errors.size()},
      {"bytes_included", bytes_included},
  };
  nlohmann::json j = {
      {"root", root},
      {"policy_fingerprint", policy_fingerprint},
      {"plan_hash", plan_hash()},
      {"summary", summary},
      {"errors", nlohmann::json::array()},
  };
  for (const auto &error : errors) j["errors"].push_back(error.to_json());
  if (include_files_value) {
    j["files"] = nlohmann::json::array();
    for (const auto &file : files) j["files"].push_back(file.to_json());
  }
  if (include_ignored_value) {
    j["ignored"] = nlohmann::json::array();
    for (const auto &entry : ignored) j["ignored"].push_back({{"relative_path", entry.path}, {"reason", entry.reason}, {"rule_id", entry.rule_id}, {"secret_protected", entry.secret_protected}});
  }
  return j;
}

ScanPlan build_scan_plan(const std::filesystem::path &repo_root_input, const ScanPlanOptions &options) {
  ScanPlan plan;
  const auto root_norm = normalize_path(repo_root_input, repo_root_input);
  plan.root = root_norm.repo_root;
  const auto root = std::filesystem::path(plan.root);
  const auto policy = load_ignore_policy(root);
  plan.policy_fingerprint = "sha256:" + policy.fingerprint();

  std::error_code ec;
  if (!std::filesystem::exists(root, ec) || !std::filesystem::is_directory(root, ec)) {
    plan.errors.push_back({plan.root, "invalid_root", "repo root does not exist or is not a directory"});
    return plan;
  }

  std::vector<std::filesystem::path> entries;
  std::filesystem::recursive_directory_iterator it(root, std::filesystem::directory_options::skip_permission_denied, ec);
  std::filesystem::recursive_directory_iterator end;
  while (!ec && it != end) {
    const auto path = it->path();
    const auto rel = safe_relative(root, path);
    const bool is_dir = it->is_directory(ec);
    const auto size = (!is_dir && !ec) ? it->file_size(ec) : 0;
    auto decision = policy.decide(rel, is_dir, size);
    ++plan.seen;
    if (decision.ignored) {
      plan.ignored.push_back(decision);
      if (is_dir) it.disable_recursion_pending();
      it.increment(ec);
      continue;
    }
    if (!is_dir && it->is_regular_file(ec)) entries.push_back(path);
    it.increment(ec);
  }
  if (ec) plan.errors.push_back({plan.root, "walk_error", ec.message()});

  std::sort(entries.begin(), entries.end(), [&](const auto &a, const auto &b) { return safe_relative(root, a) < safe_relative(root, b); });
  for (const auto &path : entries) {
    const auto rel = safe_relative(root, path);
    std::error_code sec;
    const auto size = std::filesystem::file_size(path, sec);
    if (sec) {
      plan.errors.push_back({rel, "stat_error", sec.message()});
      continue;
    }
    if (options.max_files > 0 && plan.files.size() >= options.max_files) break;
    if (options.max_bytes > 0 && plan.bytes_included + size > options.max_bytes) break;
    try {
      auto cls = classify_file(path, rel, size, policy.max_bytes);
      if (cls.binary) {
        plan.ignored.push_back({rel, true, "binary", "classifier.binary", false, "classifier"});
        continue;
      }
      ScanFile f;
      f.relative_path = rel;
      f.absolute_path = slash_path(std::filesystem::absolute(path));
      f.language = cls.language;
      f.kind = cls.kind;
      f.content_hash = sha256_file(path);
      f.size_bytes = size;
      f.mtime_ns = mtime_ns_for(path);
      plan.bytes_included += size;
      plan.files.push_back(std::move(f));
    } catch (const std::exception &exc) {
      plan.errors.push_back({rel, "scan_error", exc.what()});
    }
  }
  std::sort(plan.ignored.begin(), plan.ignored.end(), [](const auto &a, const auto &b) { return a.path < b.path; });
  return plan;
}

}  // namespace dominion_native

