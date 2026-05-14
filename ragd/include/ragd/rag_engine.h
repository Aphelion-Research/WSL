#pragma once

#include "ragd/bm25.h"
#include "ragd/storage.h"

#include <string>

namespace ragd {

class RagEngine {
 public:
  explicit RagEngine(Storage &storage);
  std::string query_json(const std::string &query, const std::string &mode, int limit);

  // Preserved for API compatibility; semantic indexes are managed by ragd_hnsw.
  void rebuild_vector();

 private:
  Storage &storage_;
  BM25Engine bm25_;
};

}  // namespace ragd
