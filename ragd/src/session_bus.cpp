#include "ragd/session_bus.h"
namespace ragd { int64_t broadcast(Storage &storage, const std::string &session_id, const std::string &channel, const std::string &message) { return storage.add_bus_message(session_id, channel, message); } }
