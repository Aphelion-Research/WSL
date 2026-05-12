#pragma once

#include "ragd/rag_engine.h"
#include "ragd/storage.h"

#include <string>

namespace ragd {

std::string mcp_manifest_json();
std::string mcp_handle_json(const std::string &body, Storage &storage, RagEngine &rag);

}  // namespace ragd
