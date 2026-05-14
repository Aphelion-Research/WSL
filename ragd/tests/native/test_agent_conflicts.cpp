#include "dominion_native/agent_conflicts.hpp"

#include <cassert>

int main() {
  dominion_native::TaskScope a;
  a.paths = {"ragd/src"};
  a.symbols = {"RagEngine"};
  dominion_native::TaskScope b;
  b.paths = {"ragd/src/rag_engine.cpp"};
  auto overlap = dominion_native::analyze_scope_overlap(a, b);
  assert(overlap.overlap);
  assert(overlap.risk == "high");
  nlohmann::json claim = {
      {"files_changed", nlohmann::json::array({"ragd/src/native/foo.cpp"})},
      {"validation_commands", nlohmann::json::array({"python -m pytest -q"})},
      {"safety_scanner_result", "pass"},
  };
  auto validation = dominion_native::validate_completion_evidence(claim);
  assert(validation["accepted"] == false);
  assert(validation["findings"].dump().find("missing_cpp_validation") != std::string::npos);
  return 0;
}

