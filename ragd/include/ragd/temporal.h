#pragma once
#include "ragd/rag_engine.h"
#include "ragd/storage.h"
#include <string>

namespace ragd {

std::string temporal_status_json();
std::string temporal_query_json(Storage &storage, RagEngine &rag, const std::string &query, const std::string &git_commit, int top_k);
std::string temporal_commits_json(Storage &storage, int limit);
std::string temporal_file_timeline_json(Storage &storage, const std::string &filepath);

}  // namespace ragd
