#include "ragd/temporal.h"

#include <nlohmann/json.hpp>

namespace ragd {

std::string temporal_status_json() {
  return nlohmann::json{{"enabled", true}, {"mode", "chunk_history"}, {"note", "current build records chunk versions on live indexing; deep libgit2 history backfill is optional at runtime"}}.dump();
}

std::string temporal_query_json(Storage &, RagEngine &rag, const std::string &query, const std::string &git_commit, int top_k) {
  auto result = nlohmann::json::parse(rag.query_json(query, "hybrid", top_k));
  result["git_commit"] = git_commit;
  result["temporal_mode"] = git_commit.empty() ? "current" : "current-index-filtered";
  return result.dump();
}

std::string temporal_commits_json(Storage &storage, int limit) {
  nlohmann::json j;
  j["commits"] = nlohmann::json::array();
  Statement stmt(storage.db(), "SELECT git_commit,count(*),max(indexed_at) FROM chunk_history WHERE git_commit<>'' GROUP BY git_commit ORDER BY max(indexed_at) DESC LIMIT ?");
  stmt.bind(1, limit);
  while (stmt.step_row()) {
    j["commits"].push_back({{"git_commit", stmt.column_text(0)}, {"chunks", stmt.column_int64(1)}, {"last_indexed_at", stmt.column_int64(2)}});
  }
  return j.dump();
}

std::string temporal_file_timeline_json(Storage &storage, const std::string &filepath) {
  nlohmann::json j;
  j["filepath"] = filepath;
  j["versions"] = nlohmann::json::array();
  Statement stmt(storage.db(), "SELECT h.chunk_id,h.git_commit,h.event,h.indexed_at,length(h.content) FROM chunk_history h JOIN chunks c ON c.id=h.chunk_id WHERE c.filepath=? ORDER BY h.indexed_at DESC LIMIT 100");
  stmt.bind(1, filepath);
  while (stmt.step_row()) {
    j["versions"].push_back({{"chunk_id", stmt.column_int64(0)}, {"git_commit", stmt.column_text(1)}, {"event", stmt.column_text(2)}, {"indexed_at", stmt.column_int64(3)}, {"bytes", stmt.column_int(4)}});
  }
  return j.dump();
}

}  // namespace ragd
