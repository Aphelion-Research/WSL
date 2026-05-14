#include "dominion_native/forbidden_tokens.hpp"

#include "dominion_native/content_hash.hpp"
#include "dominion_native/path_normalizer.hpp"

#include <algorithm>
#include <fstream>
#include <set>

namespace dominion_native {
namespace {

bool contains(const std::vector<std::string> &items, const std::string &needle) {
  return std::find(items.begin(), items.end(), needle) != items.end();
}

bool should_scan_suffix(const std::filesystem::path &path) {
  const auto ext = path.extension().generic_string();
  return ext == ".py" || ext == ".cpp" || ext == ".hpp" || ext == ".h" || ext == ".cmake" || path.filename() == "CMakeLists.txt";
}

}  // namespace

nlohmann::json ForbiddenFinding::to_json() const {
  return {{"path", path}, {"token", token}};
}

ForbiddenPolicy load_forbidden_policy(const std::filesystem::path &repo_root) {
  ForbiddenPolicy policy;
  const auto path = repo_root / "config" / "forbidden_tokens.json";
  std::ifstream in(path);
  if (!in) throw std::runtime_error("missing forbidden token policy: " + path.string());
  auto parsed = nlohmann::json::parse(in, nullptr, false);
  if (parsed.is_discarded() || !parsed.is_object()) throw std::runtime_error("invalid forbidden token policy: " + path.string());
  std::set<std::string> tokens;
  auto groups = parsed.value("groups", nlohmann::json::object());
  for (auto &[group, values] : groups.items()) {
    (void)group;
    if (!values.is_array()) continue;
    for (const auto &value : values) {
      if (value.is_string()) tokens.insert(value.get<std::string>());
    }
  }
  policy.tokens.assign(tokens.begin(), tokens.end());
  for (const auto &value : parsed.value("allowlist_files", nlohmann::json::array())) {
    if (value.is_string()) policy.allowlist_files.push_back(value.get<std::string>());
  }
  for (const auto &value : parsed.value("skip_parts", nlohmann::json::array())) {
    if (value.is_string()) policy.skip_parts.push_back(value.get<std::string>());
  }
  policy.fingerprint = sha256_string(parsed.dump());
  return policy;
}

std::vector<ForbiddenFinding> scan_forbidden_tokens(const std::filesystem::path &root, const ForbiddenPolicy &policy) {
  std::vector<ForbiddenFinding> findings;
  std::error_code ec;
  for (std::filesystem::recursive_directory_iterator it(root, std::filesystem::directory_options::skip_permission_denied, ec), end; !ec && it != end; it.increment(ec)) {
    const auto path = it->path();
    const auto rel = slash_path(std::filesystem::relative(path, root, ec));
    bool skipped = false;
    for (const auto &part : path) {
      if (contains(policy.skip_parts, part.generic_string())) {
        skipped = true;
        break;
      }
    }
    if (skipped) {
      if (it->is_directory(ec)) it.disable_recursion_pending();
      continue;
    }
    if (!it->is_regular_file(ec) || !should_scan_suffix(path)) continue;
    if (contains(policy.allowlist_files, path.filename().generic_string())) continue;
    std::ifstream in(path);
    if (!in) continue;
    const std::string text((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
    for (const auto &token : policy.tokens) {
      if (text.find(token) != std::string::npos) findings.push_back({rel, token});
    }
  }
  return findings;
}

}  // namespace dominion_native
