#include "dominion_native/vault_doctor.hpp"

#include "dominion_native/ignore_policy.hpp"
#include "dominion_native/path_normalizer.hpp"

#include <algorithm>
#include <fstream>
#include <regex>

namespace dominion_native {
namespace {

bool starts_with(const std::string &value, const std::string &prefix) {
  return value.rfind(prefix, 0) == 0;
}

bool is_url_or_anchor(const std::string &target) {
  return target.empty() || starts_with(target, "#") || starts_with(target, "http://") || starts_with(target, "https://") || starts_with(target, "mailto:");
}

std::vector<std::string> extract_links(const std::string &text) {
  std::vector<std::string> links;
  std::regex md_link(R"(\[[^\]]*\]\(([^)]+)\))");
  for (auto it = std::sregex_iterator(text.begin(), text.end(), md_link); it != std::sregex_iterator(); ++it) {
    links.push_back((*it)[1].str());
  }
  std::regex wiki_link(R"(\[\[([^\]]+)\]\])");
  for (auto it = std::sregex_iterator(text.begin(), text.end(), wiki_link); it != std::sregex_iterator(); ++it) {
    links.push_back((*it)[1].str());
  }
  return links;
}

std::string strip_fragment(std::string target) {
  const auto hash = target.find('#');
  if (hash != std::string::npos) target = target.substr(0, hash);
  const auto pipe = target.find('|');
  if (pipe != std::string::npos) target = target.substr(0, pipe);
  return target;
}

void add_example(VaultDoctorReport &report, const VaultFinding &finding) {
  if (report.examples.size() < 25) report.examples.push_back(finding);
}

}  // namespace

nlohmann::json VaultFinding::to_json() const {
  return {{"note", note}, {"link", link}, {"reason", reason}};
}

nlohmann::json VaultDoctorReport::to_json() const {
  nlohmann::json examples_json = nlohmann::json::array();
  for (const auto &example : examples) examples_json.push_back(example.to_json());
  return {
      {"ok", ok},
      {"status", status},
      {"notes", notes},
      {"broken_links", broken_links},
      {"stale_links", stale_links},
      {"outside_repo_links", outside_repo_links},
      {"secret_reference_count", secret_reference_count},
      {"examples", examples_json},
  };
}

VaultDoctorReport inspect_vault_native(const std::filesystem::path &repo_root, const std::filesystem::path &vault_dir) {
  VaultDoctorReport report;
  std::error_code ec;
  if (!std::filesystem::exists(vault_dir, ec)) {
    report.status = "skip";
    report.ok = true;
    return report;
  }
  const auto policy = load_ignore_policy(repo_root);
  std::vector<std::filesystem::path> notes;
  for (std::filesystem::recursive_directory_iterator it(vault_dir, std::filesystem::directory_options::skip_permission_denied, ec), end; !ec && it != end; it.increment(ec)) {
    if (!it->is_regular_file(ec) || it->path().extension() != ".md") continue;
    notes.push_back(it->path());
  }
  std::sort(notes.begin(), notes.end());
  report.notes = notes.size();

  for (const auto &note : notes) {
    const auto note_rel = slash_path(std::filesystem::relative(note, repo_root, ec));
    std::ifstream in(note);
    if (!in) continue;
    const std::string text((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
    if (text.find("secrets/") != std::string::npos || text.find("secrets\\") != std::string::npos) {
      ++report.secret_reference_count;
      add_example(report, {note_rel, "secrets/", "secret_reference"});
    }
    for (auto link : extract_links(text)) {
      link = strip_fragment(link);
      if (is_url_or_anchor(link)) continue;
      if (link.find("/tmp/pytest-") != std::string::npos || link.find("/tmp/pytest-of-") != std::string::npos || link.find("tmp/pytest-of-") != std::string::npos) {
        ++report.broken_links;
        ++report.stale_links;
        ++report.outside_repo_links;
        add_example(report, {note_rel, link, "outside_repo_temp_path"});
        continue;
      }
      std::filesystem::path target = link;
      if (target.is_relative()) {
        if (starts_with(link, "files/") || starts_with(link, "symbols/") || starts_with(link, "_index/") || starts_with(link, "_daily/") || starts_with(link, "_templates/")) {
          target = vault_dir / target;
        } else {
          target = note.parent_path() / target;
        }
      }
      if (target.extension().empty()) target += ".md";
      auto norm = normalize_path(repo_root, target);
      if (!norm.within_repo) {
        ++report.broken_links;
        ++report.outside_repo_links;
        add_example(report, {note_rel, link, "outside_repo"});
        continue;
      }
      const auto decision = policy.decide(norm.relative, false, 0);
      if (decision.secret_protected) {
        ++report.secret_reference_count;
        add_example(report, {note_rel, link, "secret_reference"});
        continue;
      }
      if (!std::filesystem::exists(target, ec)) {
        ++report.broken_links;
        add_example(report, {note_rel, link, "missing_target"});
      }
    }
  }
  if (report.broken_links || report.secret_reference_count) {
    report.ok = false;
    report.status = report.secret_reference_count ? "fail" : "warn";
  }
  return report;
}

}  // namespace dominion_native
