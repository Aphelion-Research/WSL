#pragma once

#include "ragd/types.h"

#include <string>
#include <vector>

namespace ragd {

class TodoEngine {
 public:
  std::vector<Todo> extract(const std::string &filepath, const std::string &content) const;
  int priority_for(const std::string &tag, const std::string &text) const;
};

}  // namespace ragd
