#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace ragd {

struct Config {
  std::string db_path;
  std::vector<std::string> index_paths;
  std::string host = "127.0.0.1";
  int port = 7474;
  std::size_t max_file_bytes = 512 * 1024;
  bool watch = false;

  static Config defaults();
  static Config from_args(int argc, char **argv);
  std::string to_json() const;
};

}  // namespace ragd
