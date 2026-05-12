#include "ragd/watcher.h"

#include <chrono>

namespace ragd {

Watcher::Watcher(Config config, Indexer &indexer) : config_(std::move(config)), indexer_(indexer) {}
Watcher::~Watcher() { stop(); }

void Watcher::start() {
  if (running_) return;
  running_ = true;
  worker_ = std::thread([this] {
    while (running_) {
      indexer_.index_paths(config_.index_paths, config_.max_file_bytes);
      std::this_thread::sleep_for(std::chrono::seconds(10));
    }
  });
}

void Watcher::stop() {
  running_ = false;
  if (worker_.joinable()) worker_.join();
}

}  // namespace ragd
