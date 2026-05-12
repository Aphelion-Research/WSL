#include "ragd/rag_engine.h"

#include <algorithm>
#include <nlohmann/json.hpp>
#include <unordered_map>

namespace ragd {

RagEngine::RagEngine(Storage &storage) : storage_(storage), bm25_(storage) {
  for (const auto &chunk : storage_.recent_chunks(5000)) vector_.add(chunk.id, chunk.content);
}

std::string RagEngine::query_json(const std::string &query, const std::string &mode, int limit) {
  std::vector<QueryResult> results;
  VectorStore fresh_vector;
  for (const auto &chunk : storage_.recent_chunks(5000)) fresh_vector.add(chunk.id, chunk.content);
  if (mode == "vector") {
    results = fresh_vector.query(query, limit);
  } else if (mode == "keyword" || mode == "bm25") {
    results = bm25_.query(query, limit);
  } else {
    auto bm = bm25_.query(query, limit * 2);
    auto vc = fresh_vector.query(query, limit * 2);
    std::unordered_map<int64_t, QueryResult> by_id;
    int rank = 1;
    for (auto &r : bm) {
      r.score += 1.0 / (60.0 + rank++);
      by_id[r.chunk_id] = r;
    }
    rank = 1;
    for (auto &r : vc) {
      auto &slot = by_id[r.chunk_id];
      if (slot.chunk_id == 0) slot = r;
      slot.vector_score = r.vector_score;
      slot.score += 1.0 / (60.0 + rank++);
    }
    for (auto &kv : by_id) results.push_back(kv.second);
    std::sort(results.begin(), results.end(), [](const auto &a, const auto &b) { return a.score > b.score; });
    if (static_cast<int>(results.size()) > limit) results.resize(limit);
  }
  nlohmann::json j;
  j["query"] = query;
  j["mode"] = mode;
  for (const auto &r : results) {
    j["results"].push_back({
        {"chunk_id", r.chunk_id},
        {"filepath", r.filepath},
        {"content", r.content},
        {"score", r.score},
        {"bm25_score", r.bm25_score},
        {"vector_score", r.vector_score},
        {"lang", r.lang},
        {"chunk_type", r.chunk_type},
        {"symbol_name", r.symbol_name},
        {"line_start", r.line_start},
        {"line_end", r.line_end},
    });
  }
  return j.dump();
}

}  // namespace ragd
