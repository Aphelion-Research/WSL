#include "ragd/config.h"
#include "ragd/http_api.h"
#include "ragd/indexer.h"
#include "ragd/rag_engine.h"
#include "ragd/storage.h"

#include <filesystem>
#include <iostream>

int main(int argc, char **argv) {
  for (int i = 1; i < argc; ++i) {
    std::string arg = argv[i];
    if (arg == "--help" || arg == "-h") {
      std::cout << "ragd --db PATH --host HOST --port PORT --path PATH [--once-health] [--index-once]\n";
      return 0;
    }
  }
  auto cfg = ragd::Config::from_args(argc, argv);
  std::filesystem::create_directories(std::filesystem::path(cfg.db_path).parent_path());
  ragd::Storage storage;
  storage.open(cfg.db_path);
  storage.initialize();
  for (int i = 1; i < argc; ++i) {
    std::string arg = argv[i];
    if (arg == "--once-health") {
      std::cout << storage.metrics_json() << "\n";
      return 0;
    }
  }
  ragd::Indexer indexer(storage);
  for (int i = 1; i < argc; ++i) {
    std::string arg = argv[i];
    if (arg == "--index-once") {
      int count = indexer.index_paths(cfg.index_paths, cfg.max_file_bytes);
      std::cout << "chunks_indexed=" << count << "\n";
      return 0;
    }
  }
  ragd::RagEngine rag(storage);
  ragd::HttpApi api(cfg, storage, indexer, rag);
  std::cout << "ragd listening on http://" << cfg.host << ":" << cfg.port << "\n";
  api.run();
  return 0;
}
