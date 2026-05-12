#include "ragd/agent_memory.h"
#include <cassert>
#include <filesystem>
int main() {
  auto db = (std::filesystem::temp_directory_path() / "ragd-test-agent.sqlite").string();
  ragd::Storage s; s.open(db); s.initialize();
  ragd::AgentMemory m(s);
  auto id = m.start("codex");
  m.touch(id, "file.cpp");
  m.remember(id, "decision");
  m.end(id);
  assert(s.handoff_json().find("decision") != std::string::npos);
  return 0;
}
