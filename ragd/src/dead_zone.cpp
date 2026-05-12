#include "ragd/dead_zone.h"

#include <filesystem>
#include <nlohmann/json.hpp>
#include <regex>
#include <set>

namespace ragd {

std::string dead_zone_report_json(Storage &storage) {
  std::set<std::string> symbols;
  std::vector<Chunk> chunks = storage.recent_chunks(20000);
  for (const auto &chunk : chunks) {
    if (!chunk.symbol_name.empty() && chunk.symbol_name != "file" && chunk.symbol_name != "document") symbols.insert(chunk.symbol_name);
  }

  nlohmann::json results = nlohmann::json::array();
  for (const auto &chunk : chunks) {
    if ((chunk.chunk_type == "function" || chunk.chunk_type == "method") && !chunk.symbol_name.empty()) {
      bool referenced = false;
      for (const auto &other : chunks) {
        if (other.id == chunk.id) continue;
        if (other.content.find(chunk.symbol_name) != std::string::npos) {
          referenced = true;
          break;
        }
      }
      if (!referenced && chunk.symbol_name != "main") {
        results.push_back({{"filepath", chunk.filepath}, {"kind", "orphaned_func"}, {"symbol_name", chunk.symbol_name}, {"detail", "symbol is indexed but not referenced by other indexed chunks"}, {"confidence", 0.62}});
      }
      if (chunk.content.find("/**") == std::string::npos && chunk.content.find("\"\"\"") == std::string::npos && chunk.content.find("///") == std::string::npos && chunk.content.find("# ") == std::string::npos) {
        results.push_back({{"filepath", chunk.filepath}, {"kind", "undocumented_public"}, {"symbol_name", chunk.symbol_name}, {"detail", "public-looking function chunk has no adjacent docstring/comment marker"}, {"confidence", 0.55}});
      }
    }

    if (chunk.lang == "markdown") {
      std::regex code_symbol(R"(`([A-Za-z_][A-Za-z0-9_]*(?:(?:::|\.)[A-Za-z_][A-Za-z0-9_]*)+)(?:\(\))?`)");
      for (auto it = std::sregex_iterator(chunk.content.begin(), chunk.content.end(), code_symbol); it != std::sregex_iterator(); ++it) {
        std::string token = (*it)[1].str();
        if (symbols.find(token) == symbols.end()) {
          results.push_back({{"filepath", chunk.filepath}, {"kind", "stale_doc"}, {"symbol_name", token}, {"detail", "markdown references a code symbol not found in the current symbol index"}, {"confidence", 0.35}});
          break;
        }
      }
    }
  }

  nlohmann::json j;
  j["dead_zones"] = results;
  j["mode"] = "heuristic";
  j["metrics"] = nlohmann::json::parse(storage.metrics_json());
  return j.dump();
}

}  // namespace ragd
