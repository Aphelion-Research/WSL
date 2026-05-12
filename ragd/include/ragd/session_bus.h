#pragma once
#include "ragd/storage.h"

namespace ragd {

int64_t broadcast(Storage &storage, const std::string &session_id, const std::string &topic, const std::string &message, const std::string &kind = "broadcast", int ttl = 0);

}  // namespace ragd
