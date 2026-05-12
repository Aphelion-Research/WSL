#pragma once

#include "ragd/storage.h"

namespace ragd {

class AgentMemory {
 public:
  explicit AgentMemory(Storage &storage) : storage_(storage) {}
  std::string start(const std::string &agent) { return storage_.start_session(agent); }
  void end(const std::string &session_id) { storage_.end_session(session_id); }
  void touch(const std::string &session_id, const std::string &filepath) { storage_.touch_file(session_id, filepath); }
  void remember(const std::string &session_id, const std::string &decision) { storage_.add_decision(session_id, decision); }

 private:
  Storage &storage_;
};

}  // namespace ragd
