#include "ragd/indexer.h"
#include <cassert>
#include <filesystem>
#include <fstream>
int main() {
  auto dir = std::filesystem::temp_directory_path() / "ragd-indexer-test";
  std::filesystem::create_directories(dir);
  std::ofstream(dir / "README.md") << "# Dominion\nTODO: index memory\n";
  auto db = (dir / "db.sqlite").string();
  ragd::Storage s; s.open(db); s.initialize();
  ragd::Indexer idx(s);
  int n = idx.index_paths({dir.string()}, 1024 * 1024);
  assert(n > 0);
  assert(!s.search_fts("Dominion", 5).empty());
  assert(!s.list_todos().empty());
  return 0;
}
