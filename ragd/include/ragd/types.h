#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace ragd {

struct Chunk {
  int64_t id = 0;
  std::string filepath;
  std::string content;
  std::string summary;
  std::string lang;
  std::string chunk_type;
  std::string symbol_name;
  std::string repo_root;
  std::string git_commit;
  int line_start = 1;
  int line_end = 1;
  std::string content_hash;
  std::string metadata_json = "{}";
  std::string status = "active";
  int64_t indexed_at = 0;
  int64_t modified_at = 0;
};

struct QueryResult {
  int64_t chunk_id = 0;
  std::string filepath;
  std::string content;
  std::string summary;
  double score = 0.0;
  double bm25_score = 0.0;
  double vector_score = 0.0;
  double rrf_score = 0.0;
  std::string lang;
  std::string chunk_type;
  std::string symbol_name;
  std::string git_commit;
  std::string content_hash;
  std::string repo_root;
  std::string status = "active";
  int64_t indexed_at = 0;
  int64_t modified_at = 0;
  int line_start = 1;
  int line_end = 1;
};

struct Todo {
  int64_t id = 0;
  std::string filepath;
  int line = 1;
  std::string tag;
  std::string text;
  std::string symbol_name;
  int priority = 5;
  std::string status = "open";
  std::string assigned_to;
  std::string content_hash;
  std::string tags_json = "[]";
};

struct Decision {
  int64_t id = 0;
  std::string session_id;
  std::string filepath;
  std::string text;
  std::string rationale;
  std::string alternatives_json = "[]";
  std::string tags_json = "[]";
  std::string created_at;
};

struct Session {
  std::string id;
  std::string agent;
  std::string started_at;
  std::string ended_at;
  std::string status;
  std::string git_branch;
  std::string git_commit;
  std::string summary;
  std::string handoff_note;
  std::string parent_session;
};

}  // namespace ragd
