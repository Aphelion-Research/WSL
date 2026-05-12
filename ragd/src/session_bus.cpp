#include "ragd/session_bus.h"

#include <nlohmann/json.hpp>

namespace ragd {

int64_t broadcast(Storage &storage, const std::string &session_id, const std::string &topic, const std::string &message, const std::string &kind, int ttl) {
  nlohmann::json payload{{"message", message}};
  return storage.add_bus_message(session_id, kind, topic, payload.dump(), ttl);
}

}  // namespace ragd
