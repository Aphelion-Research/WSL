#include "ragd/bm25.h"

namespace ragd {

std::vector<QueryResult> BM25Engine::query(const std::string &text, int limit) {
  return storage_.search_fts(text, limit);
}

}  // namespace ragd
