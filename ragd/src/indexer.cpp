#include "ragd/indexer.h"

#include "ragd/storage.h"

#include <fstream>
#include <regex>
#include <sstream>
#include <unordered_set>

namespace ragd {

namespace fs = std::filesystem;

Indexer::Indexer(Storage &storage) : storage_(storage) {}

bool Indexer::should_ignore(const fs::path &path) const {
  static const std::unordered_set<std::string> ignored = {
      ".git", "node_modules", "__pycache__", ".venv", "build", "dist", "secrets", "vendor", ".cache"};
  for (const auto &part : path) {
    auto s = part.string();
    if (ignored.count(s)) return true;
  }
  auto p = path.string();
  return p.find("data/raw") != std::string::npos || p.find("data/normalized") != std::string::npos;
}

std::string Indexer::language_for(const fs::path &path) {
  auto ext = path.extension().string();
  if (ext == ".py") return "python";
  if (ext == ".cpp" || ext == ".cc" || ext == ".cxx") return "cpp";
  if (ext == ".h" || ext == ".hpp") return "cpp";
  if (ext == ".js") return "javascript";
  if (ext == ".ts") return "typescript";
  if (ext == ".md") return "markdown";
  if (ext == ".json") return "json";
  if (ext == ".sh") return "shell";
  return "text";
}

static std::string read_file(const fs::path &path) {
  std::ifstream in(path);
  std::ostringstream ss;
  ss << in.rdbuf();
  return ss.str();
}

static std::vector<std::pair<int, std::string>> lines_of(const std::string &content) {
  std::vector<std::pair<int, std::string>> lines;
  std::istringstream in(content);
  std::string line;
  int no = 0;
  while (std::getline(in, line)) lines.push_back({++no, line});
  return lines;
}

int Indexer::index_file(const fs::path &path, std::size_t max_file_bytes) {
  if (!fs::is_regular_file(path) || should_ignore(path)) return 0;
  if (fs::file_size(path) > max_file_bytes) return 0;
  auto content = read_file(path);
  auto lang = language_for(path);
  auto filepath = fs::absolute(path).string();
  int count = 0;

  storage_.transaction([&] {
    if (lang == "markdown") {
      auto lines = lines_of(content);
      std::string chunk;
      int start = 1;
      std::string symbol = "document";
      for (const auto &[line_no, line] : lines) {
        if (!chunk.empty() && line.rfind("#", 0) == 0) {
          Chunk c{0, filepath, chunk, lang, "heading", symbol, start, line_no - 1, sha256ish(filepath + chunk)};
          storage_.upsert_chunk(c);
          ++count;
          chunk.clear();
          start = line_no;
          symbol = line;
        }
        chunk += line + "\n";
        if (line.rfind("#", 0) == 0) symbol = line;
      }
      if (!chunk.empty()) {
        Chunk c{0, filepath, chunk, lang, "heading", symbol, start, lines.empty() ? 1 : lines.back().first, sha256ish(filepath + chunk)};
        storage_.upsert_chunk(c);
        ++count;
      }
    } else {
      static const std::regex symbol_re(R"(^\s*(def|class|function|const|auto|void|int|std::string|class)\s+([A-Za-z_][A-Za-z0-9_:]*))");
      auto lines = lines_of(content);
      std::string chunk;
      int start = 1;
      std::string symbol = "file";
      int line_count = 0;
      for (const auto &[line_no, line] : lines) {
        std::smatch m;
        if (!chunk.empty() && std::regex_search(line, m, symbol_re)) {
          Chunk c{0, filepath, chunk, lang, "symbol", symbol, start, line_no - 1, sha256ish(filepath + chunk)};
          storage_.upsert_chunk(c);
          ++count;
          chunk.clear();
          start = line_no;
          line_count = 0;
          symbol = m.size() > 2 ? m[2].str() : "symbol";
        }
        if (std::regex_search(line, m, symbol_re)) symbol = m.size() > 2 ? m[2].str() : symbol;
        chunk += line + "\n";
        if (++line_count >= 120) {
          Chunk c{0, filepath, chunk, lang, "window", symbol, start, line_no, sha256ish(filepath + chunk)};
          storage_.upsert_chunk(c);
          ++count;
          chunk.clear();
          start = line_no + 1;
          line_count = 0;
        }
      }
      if (!chunk.empty()) {
        Chunk c{0, filepath, chunk, lang, "file", symbol, start, lines.empty() ? 1 : lines.back().first, sha256ish(filepath + chunk)};
        storage_.upsert_chunk(c);
        ++count;
      }
    }
    for (const auto &todo : todo_engine_.extract(filepath, content)) storage_.add_todo(todo);
  });
  return count;
}

int Indexer::index_paths(const std::vector<std::string> &paths, std::size_t max_file_bytes) {
  int count = 0;
  for (const auto &root : paths) {
    fs::path p(root);
    if (!fs::exists(p)) continue;
    if (fs::is_regular_file(p)) {
      count += index_file(p, max_file_bytes);
      continue;
    }
    for (auto it = fs::recursive_directory_iterator(p); it != fs::recursive_directory_iterator(); ++it) {
      if (should_ignore(it->path())) {
        if (it->is_directory()) it.disable_recursion_pending();
        continue;
      }
      if (it->is_regular_file()) count += index_file(it->path(), max_file_bytes);
    }
  }
  return count;
}

}  // namespace ragd
