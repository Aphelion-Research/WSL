#include "ragd/config.h"
#include "ragd/indexer.h"
#include "ragd/watcher.h"

#include <cassert>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <thread>

int main() {
  auto dir = std::filesystem::temp_directory_path() / "ragd-watcher-test";
  std::filesystem::remove_all(dir);
  std::filesystem::create_directories(dir);
  auto db = (dir / "db.sqlite").string();
  ragd::Storage s;
  s.open(db);
  s.initialize();
  ragd::Indexer idx(s);
  ragd::Config cfg = ragd::Config::defaults();
  cfg.index_paths = {dir.string()};
  cfg.max_file_bytes = 1024 * 1024;
  ragd::Watcher watcher(cfg, idx);
  watcher.start();
  std::ofstream(dir / "watched.md") << "# Watcher\ninitial content\n";
  std::this_thread::sleep_for(std::chrono::milliseconds(1200));
  auto first = s.search_fts("Watcher", 5);
  assert(!first.empty());
  std::ofstream(dir / "watched.md") << "# Watcher\nmodified unique_token\n";
  std::this_thread::sleep_for(std::chrono::milliseconds(1200));
  watcher.stop();
  auto second = s.search_fts("unique_token", 5);
  assert(!second.empty());
  return 0;
}
