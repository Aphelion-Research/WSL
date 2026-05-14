#include "dominion_native/agent_conflicts.hpp"

#include "dominion_native/path_normalizer.hpp"

#include <algorithm>
#include <set>

namespace dominion_native {
namespace {

bool intersects(const std::vector<std::string> &a, const std::vector<std::string> &b) {
  std::set<std::string> aa(a.begin(), a.end());
  for (const auto &item : b) {
    if (aa.count(item)) return true;
  }
  return false;
}

bool has_command(const nlohmann::json &claim, const std::string &needle) {
  for (const auto &cmd : claim.value("validation_commands", nlohmann::json::array())) {
    if (cmd.is_string() && cmd.get<std::string>().find(needle) != std::string::npos) return true;
  }
  return false;
}

bool any_file_ext(const nlohmann::json &claim, const std::vector<std::string> &exts) {
  for (const auto &file : claim.value("files_changed", nlohmann::json::array())) {
    if (!file.is_string()) continue;
    const auto path = file.get<std::string>();
    for (const auto &ext : exts) {
      if (path.size() >= ext.size() && path.compare(path.size() - ext.size(), ext.size(), ext) == 0) return true;
    }
  }
  return false;
}

bool any_file_contains(const nlohmann::json &claim, const std::string &needle) {
  for (const auto &file : claim.value("files_changed", nlohmann::json::array())) {
    if (file.is_string() && file.get<std::string>().find(needle) != std::string::npos) return true;
  }
  return false;
}

}  // namespace

nlohmann::json ScopeOverlap::to_json() const {
  return {{"overlap", overlap}, {"risk", risk}, {"reasons", reasons}};
}

ScopeOverlap analyze_scope_overlap(const TaskScope &a, const TaskScope &b) {
  ScopeOverlap out;
  for (const auto &pa : a.paths) {
    for (const auto &pb : b.paths) {
      if (path_has_parent_child_overlap(pa, pb)) {
        out.overlap = true;
        out.risk = "high";
        out.reasons.push_back(pa == pb ? "path_exact" : "path_parent_child");
      }
    }
  }
  if (intersects(a.symbols, b.symbols)) {
    out.overlap = true;
    if (out.risk == "none") out.risk = "medium";
    out.reasons.push_back("symbol_overlap");
  }
  if (intersects(a.packages, b.packages)) {
    out.overlap = true;
    if (out.risk == "none") out.risk = "low";
    out.reasons.push_back("package_overlap");
  }
  return out;
}

nlohmann::json validate_completion_evidence(const nlohmann::json &claim) {
  nlohmann::json findings = nlohmann::json::array();
  auto add = [&](const std::string &code, const std::string &message) { findings.push_back({{"code", code}, {"message", message}}); };
  if (!claim.contains("files_changed") || !claim["files_changed"].is_array()) add("missing_files_changed", "completion claim must list files changed");
  if (!claim.contains("validation_commands") || !claim["validation_commands"].is_array()) add("missing_validation_commands", "completion claim must list validation commands");
  if (!claim.contains("safety_scanner_result")) add("missing_safety_scanner", "completion claim must include safety scanner result");
  if (any_file_ext(claim, {".cpp", ".hpp", ".h", ".cc", ".cxx"}) && !has_command(claim, "ctest") && !has_command(claim, "cmake --build")) {
    add("missing_cpp_validation", "changed C++ files require CMake/CTest evidence");
  }
  if (any_file_contains(claim, "CMakeLists.txt") && !has_command(claim, "cmake -S")) {
    add("missing_cmake_configure", "changed CMake files require configure evidence");
  }
  if (any_file_contains(claim, "doctor") && !has_command(claim, "doctor")) {
    add("missing_doctor_validation", "changed doctor surface requires doctor command evidence");
  }
  if (any_file_contains(claim, "vault") && !has_command(claim, "vault")) {
    add("missing_vault_validation", "changed vault surface requires vault doctor evidence");
  }
  return {{"accepted", findings.empty()}, {"findings", findings}};
}

}  // namespace dominion_native

