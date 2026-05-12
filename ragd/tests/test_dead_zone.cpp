#include "ragd/dead_zone.h"

#include <cassert>
#include <filesystem>

int main() {
  auto db = (std::filesystem::temp_directory_path() / "ragd-test-dead-zone.sqlite").string();
  std::filesystem::remove(db);
  ragd::Storage s;
  s.open(db);
  s.initialize();
  ragd::Chunk c;
  c.filepath = "orphan.cpp";
  c.content = "int orphaned_func() { return 1; }\n";
  c.lang = "cpp";
  c.chunk_type = "function";
  c.symbol_name = "orphaned_func";
  c.content_hash = "dead1";
  s.upsert_chunk(c);
  auto report = ragd::dead_zone_report_json(s);
  assert(report.find("orphaned_func") != std::string::npos);
  return 0;
}
