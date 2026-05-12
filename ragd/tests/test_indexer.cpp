#include "ragd/indexer.h"
#include <cassert>
#include <filesystem>
#include <fstream>
int main() {
  auto dir = std::filesystem::temp_directory_path() / "ragd-indexer-test";
  std::filesystem::remove_all(dir);
  std::filesystem::create_directories(dir);
  auto file = dir / "README.md";
  std::ofstream(file) << "# Dominion\nTODO: index memory\n";
  auto db = (dir / "db.sqlite").string();
  ragd::Storage s; s.open(db); s.initialize();
  ragd::Indexer idx(s);
  int n = idx.index_paths({dir.string()}, 1024 * 1024);
  assert(n > 0);
  assert(!s.search_fts("Dominion", 5).empty());
  assert(!s.list_todos().empty());

  auto filepath = std::filesystem::absolute(file).string();
  auto count = [&](const std::string &sql) {
    ragd::Statement stmt(s.db(), sql);
    stmt.bind(1, filepath);
    assert(stmt.step_row());
    return stmt.column_int64(0);
  };
  auto active1 = count("SELECT count(*) FROM chunks WHERE filepath=? AND status='active'");
  auto total1 = count("SELECT count(*) FROM chunks WHERE filepath=?");
  auto fts1 = count("SELECT count(*) FROM fts_chunks WHERE filepath=?");

  int n2 = idx.index_paths({dir.string()}, 1024 * 1024);
  assert(n2 > 0);
  assert(count("SELECT count(*) FROM chunks WHERE filepath=? AND status='active'") == active1);
  assert(count("SELECT count(*) FROM chunks WHERE filepath=?") == total1);
  assert(count("SELECT count(*) FROM fts_chunks WHERE filepath=?") == fts1);
  return 0;
}
