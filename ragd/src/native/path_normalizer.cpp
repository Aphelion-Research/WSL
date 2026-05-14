#include "dominion_native/path_normalizer.hpp"

#include <algorithm>
#include <cctype>
#include <system_error>

namespace dominion_native {
namespace {

std::string normalize_slashes(std::string value) {
  std::replace(value.begin(), value.end(), '\\', '/');
  return value;
}

std::filesystem::path safe_weakly_canonical(const std::filesystem::path &path) {
  std::error_code ec;
  auto p = std::filesystem::weakly_canonical(path, ec);
  if (ec) return std::filesystem::absolute(path).lexically_normal();
  return p.lexically_normal();
}

bool starts_with_component_path(const std::string &path, const std::string &root) {
  if (path == root) return true;
  if (path.size() <= root.size()) return false;
  return path.compare(0, root.size(), root) == 0 && path[root.size()] == '/';
}

bool has_drive_prefix(const std::string &value) {
  return value.size() >= 2 && std::isalpha(static_cast<unsigned char>(value[0])) && value[1] == ':';
}

std::string lower(std::string value) {
  std::transform(value.begin(), value.end(), value.begin(), [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
  return value;
}

}  // namespace

nlohmann::json NormalizedPath::to_json() const {
  return {
      {"absolute", absolute},
      {"repo_root", repo_root},
      {"relative", relative},
      {"display", display},
      {"exists", exists},
      {"is_symlink", is_symlink},
      {"realpath", realpath},
      {"within_repo", within_repo},
      {"windows_style", windows_style},
      {"wine_path", wine_path},
      {"error", error},
  };
}

std::string slash_path(const std::filesystem::path &path) {
  return normalize_slashes(path.lexically_normal().generic_string());
}

NormalizedPath normalize_path(const std::filesystem::path &repo_root_input, const std::filesystem::path &candidate_input) {
  NormalizedPath out;
  const auto root = safe_weakly_canonical(repo_root_input);
  out.repo_root = slash_path(root);

  auto raw = normalize_slashes(candidate_input.string());
  out.windows_style = has_drive_prefix(raw) || raw.rfind("//", 0) == 0;
  const auto raw_lower = lower(raw);
  out.wine_path = raw_lower.find("/drive_c/") != std::string::npos || raw_lower.find("/dosdevices/") != std::string::npos || raw_lower.find("drive_c/") == 0;

  std::filesystem::path candidate = raw;
  if (out.windows_style && has_drive_prefix(raw)) {
    out.error = "windows_drive_path_rejected";
    out.absolute = raw;
    out.display = raw;
    return out;
  }
  if (candidate.is_relative()) candidate = root / candidate;
  candidate = candidate.lexically_normal();

  std::error_code ec;
  out.exists = std::filesystem::exists(candidate, ec);
  out.is_symlink = !ec && std::filesystem::is_symlink(candidate, ec);
  auto real = safe_weakly_canonical(candidate);
  out.absolute = slash_path(std::filesystem::absolute(candidate).lexically_normal());
  out.realpath = slash_path(real);

  auto rel = std::filesystem::relative(candidate.lexically_normal(), root, ec);
  if (ec) rel = candidate.lexically_relative(root);
  out.relative = slash_path(rel);
  out.display = out.relative.empty() || out.relative == "." ? out.repo_root : out.relative;
  out.within_repo = starts_with_component_path(out.realpath, out.repo_root) && out.relative.rfind("../", 0) != 0 && out.relative != "..";
  if (!out.within_repo && out.error.empty()) out.error = "outside_repo";
  if (out.wine_path && out.error.empty()) out.error = "wine_path_rejected";
  return out;
}

bool path_has_parent_child_overlap(const std::string &a, const std::string &b) {
  auto aa = normalize_slashes(std::filesystem::path(a).lexically_normal().generic_string());
  auto bb = normalize_slashes(std::filesystem::path(b).lexically_normal().generic_string());
  while (!aa.empty() && aa.back() == '/') aa.pop_back();
  while (!bb.empty() && bb.back() == '/') bb.pop_back();
  return starts_with_component_path(aa, bb) || starts_with_component_path(bb, aa);
}

}  // namespace dominion_native

