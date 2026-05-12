#pragma once

#include "ragd/config.h"
#include "ragd/indexer.h"

#include <atomic>
#include <thread>

namespace ragd {

class Watcher {
 public:
  Watcher(Config config, Indexer &indexer);
  ~Watcher();
  void start();
  void stop();

 private:
  Config config_;
  Indexer &indexer_;
  std::atomic<bool> running_{false};
  std::thread worker_;
};

}  // namespace ragd
