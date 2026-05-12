#include "ragd/storage.h"
#include <cassert>
#include <filesystem>

int main() {
  auto db = (std::filesystem::temp_directory_path() / "ragd-test-storage.sqlite").string();
  ragd::Storage s; s.open(db); s.initialize();
  assert(s.health_check());
  ragd::Chunk c; c.filepath = "a.md"; c.content = "hello dominion memory"; c.lang = "markdown"; c.chunk_type = "heading"; c.content_hash = ragd::sha256ish(c.content);
  auto id = s.upsert_chunk(c);
  assert(id > 0);
  auto r = s.search_fts("dominion", 5);
  assert(!r.empty());
  auto sid = s.start_session("codex");
  s.touch_file(sid, "a.md");
  s.add_decision(sid, "use sqlite fts");
  s.end_session(sid);
  ragd::Todo t; t.filepath = "a.md"; t.text = "fix thing"; t.tag = "TODO"; t.content_hash = "todo1";
  s.add_todo(t);
  assert(!s.list_todos().empty());
  return 0;
}
