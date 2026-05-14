#pragma once

#include <filesystem>
#include <nlohmann/json.hpp>
#include <string>
#include <vector>

namespace dominion_native {

struct DoctorCheck {
  std::string name;
  std::string status;
  std::string severity = "required";
  std::string message;
  nlohmann::json details = nlohmann::json::object();
  std::string remediation;

  nlohmann::json to_json() const;
};

struct DoctorOptions {
  std::filesystem::path root;
  bool offline = true;
  bool live = false;
  bool strict = false;
};

struct DoctorReport {
  std::string overall = "pass";
  std::vector<DoctorCheck> checks;

  nlohmann::json to_json() const;
  int exit_code(bool strict) const;
};

DoctorReport run_native_doctor(const DoctorOptions &options);

}  // namespace dominion_native

