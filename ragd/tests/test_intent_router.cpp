#include "ragd/intent_router.h"

#include <cassert>
#include <string>
#include <vector>

int main() {
  std::vector<std::pair<std::string, std::string>> cases = {
      {"HydraEnsemble.predict", "symbol_lookup"},
      {"where is SENTINEL defined", "general"},
      {"how does the ensemble decide exits", "conceptual"},
      {"why does indexing use fts", "conceptual"},
      {"explain ragd architecture", "conceptual"},
      {"what is the handoff protocol", "conceptual"},
      {"what changed in the last 3 sessions", "temporal"},
      {"history of watcher", "temporal"},
      {"at commit abc123", "temporal"},
      {"when was this refactored", "temporal"},
      {"todo race condition", "todo_search"},
      {"fixme in collector", "todo_search"},
      {"what needs work", "todo_search"},
      {"open issues", "todo_search"},
      {"why did we choose sqlite", "decision_search"},
      {"what was decided about mcp", "decision_search"},
      {"decision rationale", "decision_search"},
      {"unused function", "dead_code"},
      {"orphaned_func report", "dead_code"},
      {"stale docs", "dead_code"},
      {"general query text", "general"},
  };
  for (const auto &[query, expected] : cases) {
    assert(ragd::route_intent(query) == expected);
  }
  return 0;
}
