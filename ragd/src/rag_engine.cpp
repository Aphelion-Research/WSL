#include "ragd/rag_engine.h"

#include "ragd/intent_router.h"

#include <algorithm>
#include <chrono>
#include <nlohmann/json.hpp>
#include <unordered_map>

namespace ragd {

namespace {

void enrich(QueryResult &r, const std::unordered_map<int64_t, Chunk> &chunks) {
  auto it = chunks.find(r.chunk_id);
  if (it == chunks.end()) return;
  const auto &c = it->second;
  if (r.filepath.empty()) r.filepath = c.filepath;
  if (r.content.empty()) r.content = c.content;
  r.summary = c.summary;
  r.lang = c.lang;
  r.chunk_type = c.chunk_type;
  r.symbol_name = c.symbol_name;
  r.line_start = c.line_start;
  r.line_end = c.line_end;
  r.git_commit = c.git_commit;
  r.content_hash = c.content_hash;
  r.repo_root = c.repo_root;
  r.status = c.status;
  r.indexed_at = c.indexed_at;
  r.modified_at = c.modified_at;
}

nlohmann::json result_to_json(const QueryResult &r) {
  return {
      {"chunk_id", r.chunk_id},
      {"filepath", r.filepath},
      {"content", r.content},
      {"summary", r.summary},
      {"score", r.score},
      {"bm25_score", r.bm25_score},
      {"vector_score", r.vector_score},
      {"rrf_score", r.rrf_score},
      {"lang", r.lang},
      {"chunk_type", r.chunk_type},
      {"symbol_name", r.symbol_name},
      {"line_start", r.line_start},
      {"line_end", r.line_end},
      {"content_hash", r.content_hash},
      {"repo_root", r.repo_root},
      {"status", r.status},
      {"indexed_at", r.indexed_at},
      {"modified_at", r.modified_at},
      {"git_commit", r.git_commit},
  };
}

}  // namespace

RagEngine::RagEngine(Storage &storage) : storage_(storage), bm25_(storage) {
  for (const auto &chunk : storage_.recent_chunks(50000)) vector_.add(chunk.id, chunk.content);
}

std::string RagEngine::query_json(const std::string &query, const std::string &mode, int limit) {
  auto started = std::chrono::steady_clock::now();
  if (limit <= 0) limit = 10;
  std::string intent = route_intent(query);
  std::string effective_mode = mode.empty() ? "hybrid" : mode;
  if (effective_mode == "auto") {
    if (intent == "symbol_lookup") effective_mode = "bm25";
    else if (intent == "conceptual") effective_mode = "vector";
    else effective_mode = "hybrid";
  }

  std::vector<Chunk> chunks = storage_.recent_chunks(50000);
  std::unordered_map<int64_t, Chunk> by_id;
  VectorStore fresh_vector;
  for (const auto &chunk : chunks) {
    by_id.emplace(chunk.id, chunk);
    fresh_vector.add(chunk.id, chunk.content);
  }

  std::vector<QueryResult> results;
  std::string strategy = effective_mode;
  if (intent == "todo_search" && effective_mode == "hybrid") {
    nlohmann::json j;
    j["query"] = query;
    j["query_intent"] = intent;
    j["retrieval_strategy"] = "todo_engine";
    j["results"] = nlohmann::json::array();
    for (const auto &todo : storage_.list_todos_filtered("open", 99, "", limit)) {
      j["results"].push_back({{"todo_id", todo.id}, {"filepath", todo.filepath}, {"line_number", todo.line}, {"kind", todo.tag}, {"content", todo.text}, {"priority", todo.priority}, {"status", todo.status}});
    }
    j["elapsed_ms"] = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - started).count();
    return j.dump();
  }

  if (effective_mode == "vector") {
    results = fresh_vector.query(query, limit);
    for (auto &r : results) enrich(r, by_id);
    strategy = "vector_tfidf";
  } else if (effective_mode == "keyword") {
    results = storage_.search_like(query, limit);
    strategy = "keyword_like";
  } else if (effective_mode == "bm25") {
    results = bm25_.query(query, limit);
    strategy = "bm25";
  } else {
    auto bm = bm25_.query(query, 50);
    auto vc = fresh_vector.query(query, 50);
    std::unordered_map<int64_t, QueryResult> merged;
    int rank = 1;
    constexpr double k = 60.0;
    for (auto &r : bm) {
      r.rrf_score += 1.0 / (k + rank++);
      r.score = r.rrf_score + (r.bm25_score * 0.0001);
      merged[r.chunk_id] = r;
    }
    rank = 1;
    for (auto &r : vc) {
      auto &slot = merged[r.chunk_id];
      if (slot.chunk_id == 0) slot = r;
      slot.vector_score = std::max(slot.vector_score, r.vector_score);
      slot.rrf_score += 1.0 / (k + rank++);
      slot.score = slot.rrf_score + (slot.vector_score * 0.1);
    }
    for (auto &kv : merged) {
      enrich(kv.second, by_id);
      results.push_back(kv.second);
    }
    std::sort(results.begin(), results.end(), [](const auto &a, const auto &b) { return a.score > b.score; });
    if (static_cast<int>(results.size()) > limit) results.resize(limit);
    strategy = "hybrid_rrf_tfidf_rerank";
  }

  nlohmann::json j;
  j["query"] = query;
  j["mode"] = effective_mode;
  j["query_intent"] = intent;
  j["retrieval_strategy"] = strategy;
  j["results"] = nlohmann::json::array();
  for (const auto &r : results) j["results"].push_back(result_to_json(r));
  auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - started).count();
  j["elapsed_ms"] = elapsed;
  storage_.record_metric("last_query", nlohmann::json{{"q", query}, {"intent", intent}, {"strategy", strategy}, {"elapsed_ms", elapsed}}.dump());
  return j.dump();
}

}  // namespace ragd
