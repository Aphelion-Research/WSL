#pragma once
#include "ragd/storage.h"
namespace ragd { int64_t broadcast(Storage &storage, const std::string &session_id, const std::string &channel, const std::string &message); }
