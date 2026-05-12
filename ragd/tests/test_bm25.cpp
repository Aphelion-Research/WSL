#include "ragd/bm25.h"
#include <cassert>
#include <filesystem>
int main() {
  auto db = (std::filesystem::temp_directory_path() / "ragd-test-bm25.sqlite").string();
  ragd::Storage s; s.open(db); s.initialize();
  ragd::Chunk c; c.filepath="x.cpp"; c.content="gold xauusd collector"; c.lang="cpp"; c.chunk_type="file"; c.content_hash="c1"; s.upsert_chunk(c);
  ragd::BM25Engine bm(s);
  assert(!bm.query("xauusd", 3).empty());
  return 0;
}
