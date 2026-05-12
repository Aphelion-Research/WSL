#include "ragd/intent_router.h"
#include <algorithm>
namespace ragd { std::string route_intent(const std::string &text) { std::string s=text; std::transform(s.begin(), s.end(), s.begin(), ::tolower); if (s.find("todo")!=std::string::npos) return "todo"; if (s.find("handoff")!=std::string::npos) return "handoff"; if (s.find("remember")!=std::string::npos) return "memory"; return "query"; } }
