#pragma once

#include "ragd/bm25.h"
#include "ragd/storage.h"
#include "ragd/vector_store.h"

#include <string>

namespace ragd {

class RagEngine {
 public:
  explicit RagEngine(Storage &storage);
  std::string query_json(const std::string &query, const std::string &mode, int limit);

 private:
  Storage &storage_;
  BM25Engine bm25_;
  VectorStore vector_;
};

}  // namespace ragd
