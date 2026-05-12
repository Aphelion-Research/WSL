#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace ragd {

struct Chunk {
  int64_t id = 0;
  std::string filepath;
  std::string content;
  std::string lang;
  std::string chunk_type;
  std::string symbol_name;
  int line_start = 1;
  int line_end = 1;
  std::string content_hash;
  std::string metadata_json = "{}";
  std::string status = "active";
};

struct QueryResult {
  int64_t chunk_id = 0;
  std::string filepath;
  std::string content;
  double score = 0.0;
  double bm25_score = 0.0;
  double vector_score = 0.0;
  std::string lang;
  std::string chunk_type;
  std::string symbol_name;
  int line_start = 1;
  int line_end = 1;
};

struct Todo {
  int64_t id = 0;
  std::string filepath;
  int line = 1;
  std::string tag;
  std::string text;
  int priority = 5;
  std::string status = "open";
  std::string content_hash;
};

struct Decision {
  int64_t id = 0;
  std::string session_id;
  std::string text;
  std::string created_at;
};

struct Session {
  std::string id;
  std::string agent;
  std::string started_at;
  std::string ended_at;
  std::string status;
};

}  // namespace ragd
