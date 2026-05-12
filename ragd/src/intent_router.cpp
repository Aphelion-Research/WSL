#include "ragd/intent_router.h"

#include <algorithm>
#include <cctype>
#include <regex>

namespace ragd {

std::string route_intent(const std::string &text) {
  std::string s = text;
  std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) { return static_cast<char>(std::tolower(c)); });

  auto has = [&](const std::string &needle) { return s.find(needle) != std::string::npos; };
  if (has("todo") || has("fixme") || has("what needs") || has("open issue")) return "todo_search";
  if (has("why did") || has("what was decided") || has("rationale") || has("decision")) return "decision_search";
  if (has("before") || has("last week") || has("at commit") || has("when was") || has("history") || has("changed in")) return "temporal";
  if (has("orphaned") || has("unused") || has("dead") || has("stale")) return "dead_code";
  if (has("how does") || has("why does") || has("explain") || has("what is") || has("architecture")) return "conceptual";

  static const std::regex symbol_pattern(R"(^\s*[A-Za-z_][A-Za-z0-9_:]*(\.[A-Za-z_][A-Za-z0-9_]*)?\s*$)");
  if (std::regex_match(text, symbol_pattern)) return "symbol_lookup";
  if (text.find("::") != std::string::npos || text.find(".") != std::string::npos) return "symbol_lookup";
  return "general";
}

}  // namespace ragd
