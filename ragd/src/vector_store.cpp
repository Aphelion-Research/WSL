#include "ragd/vector_store.h"

#include <algorithm>
#include <cmath>
#include <regex>
#include <unordered_set>

namespace ragd {

std::vector<std::string> tokenize(const std::string &text) {
  static const std::regex word("[A-Za-z0-9_]+");
  std::vector<std::string> out;
  for (auto it = std::sregex_iterator(text.begin(), text.end(), word); it != std::sregex_iterator(); ++it) {
    std::string token = it->str();
    std::transform(token.begin(), token.end(), token.begin(), ::tolower);
    if (token.size() > 1) out.push_back(token);
  }
  return out;
}

static std::unordered_map<std::string, double> tf(const std::string &text) {
  std::unordered_map<std::string, double> v;
  for (const auto &t : tokenize(text)) v[t] += 1.0;
  double norm = 0.0;
  for (const auto &kv : v) norm += kv.second * kv.second;
  norm = std::sqrt(norm);
  if (norm > 0) for (auto &kv : v) kv.second /= norm;
  return v;
}

double cosine(const std::unordered_map<std::string, double> &a, const std::unordered_map<std::string, double> &b) {
  double score = 0.0;
  const auto &small = a.size() < b.size() ? a : b;
  const auto &large = a.size() < b.size() ? b : a;
  for (const auto &kv : small) {
    auto it = large.find(kv.first);
    if (it != large.end()) score += kv.second * it->second;
  }
  return score;
}

void VectorStore::add(int64_t id, const std::string &text) {
  documents_[id] = tf(text);
  contents_[id] = text;
}

std::vector<QueryResult> VectorStore::query(const std::string &text, int limit) const {
  auto q = tf(text);
  std::vector<QueryResult> out;
  for (const auto &kv : documents_) {
    QueryResult r;
    r.chunk_id = kv.first;
    r.vector_score = cosine(q, kv.second);
    r.score = r.vector_score;
    auto text_it = contents_.find(kv.first);
    if (text_it != contents_.end()) r.content = text_it->second;
    out.push_back(std::move(r));
  }
  std::sort(out.begin(), out.end(), [](const auto &a, const auto &b) { return a.score > b.score; });
  if (static_cast<int>(out.size()) > limit) out.resize(limit);
  return out;
}

}  // namespace ragd
