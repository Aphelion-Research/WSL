#pragma once

#include "ragd/storage.h"

namespace ragd {

class BM25Engine {
 public:
  explicit BM25Engine(Storage &storage) : storage_(storage) {}
  std::vector<QueryResult> query(const std::string &text, int limit);

 private:
  Storage &storage_;
};

}  // namespace ragd
