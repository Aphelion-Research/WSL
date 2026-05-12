#include "ragd/rag_engine.h"
#include <cassert>
#include <filesystem>
int main() {
  auto db = (std::filesystem::temp_directory_path() / "ragd-test-rag.sqlite").string();
  ragd::Storage s; s.open(db); s.initialize();
  ragd::Chunk c; c.filepath="doc.md"; c.content="persistent agent memory"; c.lang="markdown"; c.chunk_type="heading"; c.content_hash="r1"; s.upsert_chunk(c);
  ragd::RagEngine r(s);
  auto json = r.query_json("agent memory", "hybrid", 5);
  assert(json.find("agent memory") != std::string::npos);
  return 0;
}
