#include "ragd/todo_engine.h"

#include "ragd/storage.h"

#include <regex>
#include <sstream>

namespace ragd {

int TodoEngine::priority_for(const std::string &tag, const std::string &text) const {
  std::string upper = tag + " " + text;
  for (auto &c : upper) c = static_cast<char>(::toupper(c));
  if (upper.find("CRASH") != std::string::npos || upper.find("RACE") != std::string::npos || upper.find("DEADLOCK") != std::string::npos || upper.find("LEAK") != std::string::npos || upper.find("PANIC") != std::string::npos || upper.find("UNDEFINED BEHAVIOR") != std::string::npos) return 1;
  if (tag == "SECURITY") return 1;
  if (upper.find("LIVE") != std::string::npos || upper.find("PROD") != std::string::npos || upper.find("TRADING") != std::string::npos || upper.find("MONEY") != std::string::npos || upper.find("RISK") != std::string::npos) return 2;
  if (tag == "BUG" || tag == "FIXME") return 2;
  if (tag == "HACK") return 3;
  if (tag == "PERF" || tag == "OPTIMIZE") return 4;
  return 5;
}

std::vector<Todo> TodoEngine::extract(const std::string &filepath, const std::string &content) const {
  static const std::regex marker(R"((TODO|FIXME|HACK|NOTE|BUG|OPTIMIZE|PERF|SECURITY|WARN|DEPRECATED)[: ](.*))");
  std::vector<Todo> out;
  std::istringstream in(content);
  std::string line;
  int line_no = 0;
  while (std::getline(in, line)) {
    ++line_no;
    std::smatch m;
    if (std::regex_search(line, m, marker)) {
      Todo t;
      t.filepath = filepath;
      t.line = line_no;
      t.tag = m[1].str();
      t.text = m[2].str();
      t.priority = priority_for(t.tag, t.text);
      t.status = "open";
      t.content_hash = sha256ish(filepath + ":" + std::to_string(line_no) + ":" + t.tag + ":" + t.text);
      out.push_back(std::move(t));
    }
  }
  return out;
}

}  // namespace ragd
