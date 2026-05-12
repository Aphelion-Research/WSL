#pragma once

#include "ragd/config.h"
#include "ragd/indexer.h"
#include "ragd/rag_engine.h"
#include "ragd/storage.h"

namespace ragd {

class HttpApi {
 public:
  HttpApi(Config config, Storage &storage, Indexer &indexer, RagEngine &rag);
  void run();

 private:
  Config config_;
  Storage &storage_;
  Indexer &indexer_;
  RagEngine &rag_;
};

}  // namespace ragd
