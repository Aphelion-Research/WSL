#include "ragd/rag_engine.h"
#include <cassert>
#include <filesystem>
#include <nlohmann/json.hpp>
int main() {
  auto db = (std::filesystem::temp_directory_path() / "ragd-test-rag.sqlite").string();
  std::filesystem::remove(db);
  ragd::Storage s; s.open(db); s.initialize();
  ragd::Chunk c; c.filepath="doc.md"; c.content="persistent agent memory"; c.lang="markdown"; c.chunk_type="heading"; c.content_hash="r1"; c.repo_root="/tmp/ragd-test-root"; c.indexed_at=1234567890; c.modified_at=1234567800; s.upsert_chunk(c);
  ragd::RagEngine r(s);
  auto json = r.query_json("agent memory", "hybrid", 5);
  assert(json.find("agent memory") != std::string::npos);
  auto parsed = nlohmann::json::parse(json);
  assert(!parsed["results"].empty());
  auto result = parsed["results"][0];
  assert(result["content_hash"] == "r1");
  assert(result["repo_root"] == "/tmp/ragd-test-root");
  assert(result["document_id"].is_string());
  assert(result["stable_chunk_id"].is_string());
  assert(result["relative_path"] == "doc.md");
  assert(result["language"] == "markdown");
  assert(result["source_subsystem"] == "ragd");
  assert(result["score_breakdown"].is_object());
  assert(result["status"] == "active");
  assert(result["indexed_at"] == 1234567890);
  assert(result["modified_at"] == 1234567800);
  return 0;
}
