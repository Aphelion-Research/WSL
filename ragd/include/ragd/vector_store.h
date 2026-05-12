#pragma once

#include "ragd/types.h"

#include <string>
#include <unordered_map>
#include <vector>

namespace ragd {

class VectorStore {
 public:
  void add(int64_t id, const std::string &text);
  std::vector<QueryResult> query(const std::string &text, int limit) const;
  std::size_t size() const { return documents_.size(); }

 private:
  std::unordered_map<int64_t, std::unordered_map<std::string, double>> documents_;
  std::unordered_map<int64_t, std::string> contents_;
};

std::vector<std::string> tokenize(const std::string &text);
double cosine(const std::unordered_map<std::string, double> &a, const std::unordered_map<std::string, double> &b);

}  // namespace ragd
