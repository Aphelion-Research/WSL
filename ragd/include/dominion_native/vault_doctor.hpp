#pragma once

#include <filesystem>
#include <nlohmann/json.hpp>
#include <string>
#include <vector>

namespace dominion_native {

struct VaultFinding {
  std::string note;
  std::string link;
  std::string reason;

  nlohmann::json to_json() const;
};

struct VaultDoctorReport {
  bool ok = true;
  std::string status = "pass";
  std::size_t notes = 0;
  std::size_t broken_links = 0;
  std::size_t stale_links = 0;
  std::size_t outside_repo_links = 0;
  std::size_t secret_reference_count = 0;
  std::vector<VaultFinding> examples;

  nlohmann::json to_json() const;
};

VaultDoctorReport inspect_vault_native(const std::filesystem::path &repo_root, const std::filesystem::path &vault_dir);

}  // namespace dominion_native

