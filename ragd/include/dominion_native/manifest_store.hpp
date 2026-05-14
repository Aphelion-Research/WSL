#pragma once

#include "dominion_native/scan_plan.hpp"
#include "ragd/sqlite_compat.h"

#include <filesystem>
#include <nlohmann/json.hpp>
#include <string>

namespace dominion_native {

class ManifestStore {
 public:
  ManifestStore() = default;
  ~ManifestStore();
  ManifestStore(const ManifestStore &) = delete;
  ManifestStore &operator=(const ManifestStore &) = delete;

  void open(const std::filesystem::path &db_path);
  void initialize();
  std::string commit_scan(const ScanPlan &plan);
  nlohmann::json doctor_json();

 private:
  sqlite3 *db_ = nullptr;
  void exec(const std::string &sql);
};

nlohmann::json manifest_init_json(const std::filesystem::path &db_path);
nlohmann::json manifest_scan_json(const std::filesystem::path &db_path, const std::filesystem::path &repo_root);
nlohmann::json manifest_doctor_json(const std::filesystem::path &db_path);

}  // namespace dominion_native
