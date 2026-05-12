#include "ragd/indexer.h"
#include "ragd/rag_engine.h"
#include "ragd/temporal.h"

#include <cassert>
#include <filesystem>
#include <fstream>

int main() {
  auto dir = std::filesystem::temp_directory_path() / "ragd-temporal-test";
  std::filesystem::remove_all(dir);
  std::filesystem::create_directories(dir);
  std::ofstream(dir / "note.md") << "# Timeline\nTemporal memory chunk\n";
  auto db = (dir / "db.sqlite").string();
  ragd::Storage s;
  s.open(db);
  s.initialize();
  ragd::Indexer idx(s);
  assert(idx.index_paths({dir.string()}, 1024 * 1024) > 0);
  ragd::RagEngine rag(s);
  assert(ragd::temporal_status_json().find("enabled") != std::string::npos);
  assert(ragd::temporal_query_json(s, rag, "Temporal memory", "HEAD", 3).find("Temporal memory") != std::string::npos);
  assert(ragd::temporal_file_timeline_json(s, (dir / "note.md").string()).find("versions") != std::string::npos);
  return 0;
}
