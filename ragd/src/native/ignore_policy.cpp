#include "dominion_native/ignore_policy.hpp"

#include "dominion_native/content_hash.hpp"
#include "dominion_native/path_normalizer.hpp"

#include <algorithm>
#include <fstream>
#include <unordered_set>

namespace dominion_native {
namespace {

template <typename T>
bool contains(const std::vector<T> &items, const T &needle) {
  return std::find(items.begin(), items.end(), needle) != items.end();
}

std::string lower(std::string value) {
  std::transform(value.begin(), value.end(), value.begin(), [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
  return value;
}

std::vector<std::string> strings_from_json(const nlohmann::json &j) {
  std::vector<std::string> out;
  if (!j.is_array()) return out;
  for (const auto &v : j) {
    if (v.is_string()) out.push_back(v.get<std::string>());
  }
  std::sort(out.begin(), out.end());
  out.erase(std::unique(out.begin(), out.end()), out.end());
  return out;
}

bool regex_matches_any(const std::vector<std::string> &patterns, const std::string &path, std::string *pattern_out) {
  for (const auto &pattern : patterns) {
    try {
      if (std::regex_search(path, std::regex(pattern))) {
        if (pattern_out) *pattern_out = pattern;
        return true;
      }
    } catch (const std::regex_error &) {
      continue;
    }
  }
  return false;
}

std::vector<std::string> path_parts(const std::filesystem::path &path) {
  std::vector<std::string> parts;
  for (const auto &part : path) {
    auto value = part.generic_string();
    if (!value.empty() && value != ".") parts.push_back(value);
  }
  return parts;
}

}  // namespace

nlohmann::json IgnoreDecision::to_json() const {
  return {
      {"path", path},
      {"ignored", ignored},
      {"reason", reason},
      {"rule_id", rule_id},
      {"secret_protected", secret_protected},
      {"source", source},
  };
}

IgnorePolicy default_ignore_policy() {
  IgnorePolicy policy;
  policy.dir_deny = {
      ".cache", ".eggs", ".git", ".hg", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".svn", ".tox", ".venv",
      "__pycache__", "apps", "build", "dist", "dosdevices", "drive_c", "eggs", "node_modules", "secrets", "vendor", "venv"};
  policy.ext_deny = {
      ".7z", ".avi", ".bin", ".bmp", ".bz2", ".db", ".db3", ".dll", ".duckdb", ".dylib", ".egg", ".exe", ".flac",
      ".ggml", ".gguf", ".gif", ".gz", ".ico", ".img", ".iso", ".jpeg", ".jpg", ".mkv", ".mov", ".mp3", ".mp4",
      ".npy", ".npz", ".onnx", ".pdf", ".pickle", ".pkl", ".png", ".pt", ".pth", ".pyc", ".pyo", ".so", ".sqlite",
      ".sqlite3", ".tar", ".wav", ".webp", ".whl", ".xz", ".zip"};
  policy.path_deny = {
      R"((?:^|[/\\])data[/\\]raw[/\\])",
      R"((?:^|[/\\])data[/\\]normalized[/\\])",
      R"((?:^|[/\\])secrets[/\\])",
      R"((?:^|[/\\])backups[/\\])",
      R"((?:^|[/\\])models[/\\]active[/\\])",
      R"((?:^|[/\\])\.ragd[/\\])",
      R"([^/\\][/\\]tmp[/\\])"};
  std::sort(policy.dir_deny.begin(), policy.dir_deny.end());
  std::sort(policy.ext_deny.begin(), policy.ext_deny.end());
  return policy;
}

IgnorePolicy load_ignore_policy(const std::filesystem::path &repo_root) {
  IgnorePolicy policy = default_ignore_policy();
  const auto path = repo_root / "config" / "dominion_ignore_policy.json";
  std::ifstream in(path);
  if (!in) return policy;
  auto parsed = nlohmann::json::parse(in, nullptr, false);
  if (parsed.is_discarded()) return policy;
  auto p = parsed.contains("policy") ? parsed["policy"] : parsed;
  if (!p.is_object()) return policy;
  policy.version = p.value("version", 1);
  policy.dir_deny = strings_from_json(p.value("dir_deny", nlohmann::json::array()));
  policy.ext_deny = strings_from_json(p.value("ext_deny", nlohmann::json::array()));
  policy.path_deny = strings_from_json(p.value("path_deny", nlohmann::json::array()));
  policy.max_bytes = p.value("max_bytes", policy.max_bytes);
  policy.secrets_always_ignored = p.value("secrets_always_ignored", true);
  policy.source = "policy_file";
  policy.config_hash = parsed.value("policy_hash", "");
  return policy;
}

IgnoreDecision IgnorePolicy::decide(const std::filesystem::path &relative_path, bool is_directory, std::uintmax_t size_bytes) const {
  IgnoreDecision decision;
  decision.path = slash_path(relative_path);
  decision.source = source;
  const auto parts = path_parts(relative_path);
  for (const auto &part : parts) {
    if (contains(dir_deny, part)) {
      decision.ignored = true;
      decision.reason = part == "secrets" ? "secret_protected" : "directory:" + part;
      decision.rule_id = part == "secrets" ? "default.secrets" : "default.dir_deny." + part;
      decision.secret_protected = part == "secrets";
      return decision;
    }
  }
  std::string pattern;
  if (regex_matches_any(path_deny, decision.path, &pattern)) {
    decision.ignored = true;
    decision.reason = pattern.find("secrets") != std::string::npos ? "secret_protected" : "path_pattern";
    decision.rule_id = "default.path_deny";
    decision.secret_protected = pattern.find("secrets") != std::string::npos;
    return decision;
  }
  const auto ext = lower(relative_path.extension().generic_string());
  if (!is_directory && !ext.empty() && contains(ext_deny, ext)) {
    decision.ignored = true;
    decision.reason = "extension:" + ext;
    decision.rule_id = "default.ext_deny" + ext;
    return decision;
  }
  const auto name = relative_path.filename().generic_string();
  if (!name.empty() && name[0] == '.' && name != ".env.example" && name != ".dominionignore") {
    decision.ignored = true;
    decision.reason = "hidden_path";
    decision.rule_id = "default.hidden";
    return decision;
  }
  if (!is_directory && max_bytes > 0 && size_bytes > max_bytes) {
    decision.ignored = true;
    decision.reason = "size_limit";
    decision.rule_id = "default.max_bytes";
    return decision;
  }
  decision.reason = "included";
  return decision;
}

nlohmann::json IgnorePolicy::policy_json() const {
  return {
      {"dir_deny", dir_deny},
      {"ext_deny", ext_deny},
      {"max_bytes", max_bytes},
      {"path_deny", path_deny},
      {"secrets_always_ignored", secrets_always_ignored},
      {"version", version},
  };
}

std::string IgnorePolicy::fingerprint() const {
  const auto computed = sha256_string(policy_json().dump());
  if (!config_hash.empty()) return config_hash;
  return computed;
}

}  // namespace dominion_native

