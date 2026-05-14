#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace ragd {

struct Config {
  std::string db_path;
  std::string vector_index_path;
  std::string unix_socket = "/tmp/ragd.sock";
  std::vector<std::string> index_paths;
  std::vector<std::string> ignore_patterns;
  std::vector<std::string> extensions;
  std::string host = "0.0.0.0";
  int port = 7474;
  int max_connections = 64;
  int request_timeout_ms = 30000;
  int embed_dim = 3072;
  int bm25_candidates = 50;
  int vector_candidates = 50;
  int rrf_k = 60;
  int default_top_k = 10;
  int temporal_commits = 50;
  int dead_zone_scan_hours = 6;
  std::size_t max_file_bytes = 10 * 1024 * 1024;
  std::string embedding_provider = "voyage";
  std::string embed_backend_selected = "external";
  std::string embedding_model = "voyage-code-2";
  std::string embedding_api_key_env = "RAGD_EMBED_API_KEY";
  std::string log_level = "info";
  std::string log_file;
  bool temporal_enabled = true;
  bool dead_zone_auto_scan = true;
  bool cache_embeddings = true;
  bool watch = false;

  static Config defaults();
  static Config from_file(const std::string &path);
  static Config from_args(int argc, char **argv);
  std::string to_json() const;
};

}  // namespace ragd
