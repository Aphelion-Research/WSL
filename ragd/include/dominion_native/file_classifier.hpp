#pragma once

#include <filesystem>
#include <nlohmann/json.hpp>
#include <string>

namespace dominion_native {

struct FileClassification {
  std::string path;
  std::string kind = "unknown";
  std::string language = "unknown";
  bool binary = false;
  bool text = true;
  std::string encoding = "utf-8";
  bool large = false;
  bool generated = false;
  std::string reason = "unknown";

  nlohmann::json to_json() const;
};

FileClassification classify_file(const std::filesystem::path &absolute_path, const std::string &relative_path, std::uintmax_t size_bytes, std::size_t large_threshold = 512 * 1024);

}  // namespace dominion_native

