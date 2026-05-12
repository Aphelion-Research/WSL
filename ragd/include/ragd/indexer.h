#pragma once

#include "ragd/config.h"
#include "ragd/storage.h"
#include "ragd/todo_engine.h"

#include <filesystem>
#include <string>
#include <vector>

namespace ragd {

class Indexer {
 public:
  explicit Indexer(Storage &storage);
  int index_paths(const std::vector<std::string> &paths, std::size_t max_file_bytes);
  int index_file(const std::filesystem::path &path, std::size_t max_file_bytes);
  bool should_ignore(const std::filesystem::path &path) const;
  static std::string language_for(const std::filesystem::path &path);

 private:
  Storage &storage_;
  TodoEngine todo_engine_;
};

}  // namespace ragd
