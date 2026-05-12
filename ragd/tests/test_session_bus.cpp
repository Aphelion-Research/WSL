#include "ragd/session_bus.h"

#include <cassert>
#include <filesystem>

int main() {
  auto db = (std::filesystem::temp_directory_path() / "ragd-test-session-bus.sqlite").string();
  std::filesystem::remove(db);
  ragd::Storage s;
  s.open(db);
  s.initialize();
  auto sid = s.start_session("agent-a");
  auto id = ragd::broadcast(s, sid, "warnings", "do not edit file.cpp", "warning", 60);
  assert(id > 0);
  auto messages = s.bus_messages_json("warnings", 0);
  assert(messages.find("do not edit") != std::string::npos);
  s.add_bus_message(sid, "lock", "file.cpp", R"({"message":"locking"})", 60);
  assert(s.bus_locks_json().find("file.cpp") != std::string::npos);
  s.add_bus_message(sid, "unlock", "file.cpp", R"({"message":"unlocking"})", 60);
  assert(s.bus_locks_json().find("file.cpp") == std::string::npos);
  return 0;
}
