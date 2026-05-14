#include "ragd/indexer.h"

#include "ragd/storage.h"

#include <algorithm>
#include <chrono>
#include <cctype>
#include <fstream>
#include <nlohmann/json.hpp>
#include <regex>
#include <sstream>
#include <unordered_set>

namespace ragd {

namespace fs = std::filesystem;

namespace {

std::string read_file(const fs::path &path) {
  std::ifstream in(path);
  std::ostringstream ss;
  ss << in.rdbuf();
  return ss.str();
}

std::vector<std::pair<int, std::string>> lines_of(const std::string &content) {
  std::vector<std::pair<int, std::string>> lines;
  std::istringstream in(content);
  std::string line;
  int no = 0;
  while (std::getline(in, line)) lines.push_back({++no, line});
  return lines;
}

std::string trim(std::string s) {
  auto not_space = [](unsigned char c) { return !std::isspace(c); };
  s.erase(s.begin(), std::find_if(s.begin(), s.end(), not_space));
  s.erase(std::find_if(s.rbegin(), s.rend(), not_space).base(), s.end());
  return s;
}

int indent_of(const std::string &line) {
  int n = 0;
  for (char c : line) {
    if (c == ' ') ++n;
    else if (c == '\t') n += 4;
    else break;
  }
  return n;
}

std::vector<std::string> regex_values(const std::string &content, const std::regex &re, std::size_t group = 1) {
  std::vector<std::string> out;
  for (auto it = std::sregex_iterator(content.begin(), content.end(), re); it != std::sregex_iterator(); ++it) {
    if (it->size() > group) out.push_back((*it)[group].str());
  }
  return out;
}

nlohmann::json metadata_for(const std::string &content, const std::string &parent = "", const std::string &docstring = "") {
  nlohmann::json meta;
  meta["parent_class"] = parent;
  meta["docstring"] = docstring;
  meta["calls"] = regex_values(content, std::regex(R"(\b([A-Za-z_][A-Za-z0-9_]*)\s*\()"));
  meta["imports"] = regex_values(content, std::regex(R"((?:from|import|#include)\s+([A-Za-z0-9_./<>]+))"));
  return meta;
}

void emit_chunk(std::vector<Chunk> &chunks, const std::string &filepath, const std::string &lang, const std::string &type, const std::string &symbol, int start, int end, const std::vector<std::pair<int, std::string>> &lines, const std::string &parent = "") {
  if (start <= 0 || end < start || lines.empty()) return;
  std::ostringstream content;
  for (const auto &[line_no, line] : lines) {
    if (line_no >= start && line_no <= end) content << line << "\n";
  }
  auto text = content.str();
  if (trim(text).empty()) return;
  Chunk c;
  c.filepath = filepath;
  c.content = text;
  c.lang = lang;
  c.chunk_type = type;
  c.symbol_name = symbol;
  c.line_start = start;
  c.line_end = end;
  c.content_hash = sha256ish(filepath + ":" + std::to_string(start) + ":" + std::to_string(end) + ":" + text);
  c.metadata_json = metadata_for(text, parent).dump();
  c.status = "active";
  chunks.push_back(std::move(c));
}

std::vector<Chunk> chunk_markdown(const std::string &filepath, const std::string &content) {
  std::vector<Chunk> chunks;
  auto lines = lines_of(content);
  int start = 1;
  std::string symbol = "document";
  for (const auto &[line_no, line] : lines) {
    if (line.rfind("#", 0) == 0 && line_no != start) {
      emit_chunk(chunks, filepath, "markdown", "section", symbol, start, line_no - 1, lines);
      start = line_no;
      symbol = trim(line);
    } else if (line.rfind("#", 0) == 0) {
      symbol = trim(line);
    }
  }
  if (!lines.empty()) emit_chunk(chunks, filepath, "markdown", "section", symbol, start, lines.back().first, lines);
  return chunks;
}

std::vector<Chunk> chunk_config(const std::string &filepath, const std::string &content, const std::string &lang) {
  std::vector<Chunk> chunks;
  auto lines = lines_of(content);
  std::regex top_key(R"(^\s*["']?([A-Za-z0-9_.-]+)["']?\s*[:=])");
  int start = 1;
  std::string symbol = "config";
  for (const auto &[line_no, line] : lines) {
    std::smatch m;
    if (std::regex_search(line, m, top_key) && indent_of(line) == 0) {
      if (line_no != start) emit_chunk(chunks, filepath, lang, "config_block", symbol, start, line_no - 1, lines);
      start = line_no;
      symbol = m[1].str();
    }
  }
  if (!lines.empty()) emit_chunk(chunks, filepath, lang, "config_block", symbol, start, lines.back().first, lines);
  return chunks;
}

std::vector<Chunk> chunk_code(const std::string &filepath, const std::string &content, const std::string &lang) {
  std::vector<Chunk> chunks;
  auto lines = lines_of(content);
  if (lines.empty()) return chunks;

  std::regex py_symbol(R"(^(\s*)(class|def)\s+([A-Za-z_][A-Za-z0-9_]*)\s*[\(:])");
  std::regex cpp_class(R"(^\s*(class|struct)\s+([A-Za-z_][A-Za-z0-9_:]*))");
  std::regex cpp_func(R"(^\s*(?:template\s*<[^>]+>\s*)?(?:static\s+|inline\s+|constexpr\s+|virtual\s+|extern\s+)?[A-Za-z_][A-Za-z0-9_:<>,\s*&~]+\s+([A-Za-z_][A-Za-z0-9_:~]*)\s*\([^;]*\)\s*(?:const\s*)?(?:\{|$))");

  struct SymbolStart {
    int line;
    int indent;
    std::string type;
    std::string symbol;
    std::string parent;
  };
  std::vector<SymbolStart> starts;
  std::string current_class;
  int current_class_indent = -1;

  for (const auto &[line_no, line] : lines) {
    std::smatch m;
    if (lang == "python" && std::regex_search(line, m, py_symbol)) {
      int indent = static_cast<int>(m[1].str().size());
      std::string kind = m[2].str();
      std::string name = m[3].str();
      if (!current_class.empty() && indent <= current_class_indent) current_class.clear();
      std::string parent;
      std::string type = kind == "class" ? "class" : "function";
      if (kind == "class") {
        current_class = name;
        current_class_indent = indent;
      } else if (!current_class.empty() && indent > current_class_indent) {
        parent = current_class;
        type = "method";
        name = current_class + "." + name;
      }
      starts.push_back({line_no, indent, type, name, parent});
    } else if ((lang == "cpp" || lang == "rust" || lang == "typescript" || lang == "javascript" || lang == "go") && std::regex_search(line, m, cpp_class)) {
      starts.push_back({line_no, indent_of(line), "class", m[2].str(), ""});
    } else if ((lang == "cpp" || lang == "typescript" || lang == "javascript" || lang == "go") && std::regex_search(line, m, cpp_func)) {
      starts.push_back({line_no, indent_of(line), "function", m[1].str(), ""});
    } else if (lang == "rust") {
      std::regex rust_func(R"(^\s*(?:pub\s+)?fn\s+([A-Za-z_][A-Za-z0-9_]*)\s*\()");
      if (std::regex_search(line, m, rust_func)) starts.push_back({line_no, indent_of(line), "function", m[1].str(), ""});
    }
  }

  if (starts.empty()) {
    int start = 1;
    int count = 0;
    for (const auto &[line_no, line] : lines) {
      (void)line;
      if (++count >= 120) {
        emit_chunk(chunks, filepath, lang, "block", "file", start, line_no, lines);
        start = line_no + 1;
        count = 0;
      }
    }
    if (start <= lines.back().first) emit_chunk(chunks, filepath, lang, "block", "file", start, lines.back().first, lines);
    return chunks;
  }

  if (starts.front().line > 1) emit_chunk(chunks, filepath, lang, "block", "top_level", 1, starts.front().line - 1, lines);
  for (std::size_t i = 0; i < starts.size(); ++i) {
    int end = (i + 1 < starts.size()) ? starts[i + 1].line - 1 : lines.back().first;
    emit_chunk(chunks, filepath, lang, starts[i].type, starts[i].symbol, starts[i].line, end, lines, starts[i].parent);
  }
  return chunks;
}

std::string git_root_for(fs::path path) {
  if (fs::is_regular_file(path)) path = path.parent_path();
  while (!path.empty()) {
    if (fs::exists(path / ".git")) return fs::absolute(path).string();
    if (path == path.root_path()) break;
    path = path.parent_path();
  }
  return "";
}

std::string git_head_for(const std::string &root) {
  if (root.empty()) return "";
  fs::path git = fs::path(root) / ".git";
  fs::path head = git / "HEAD";
  if (!fs::exists(head)) return "";
  std::ifstream in(head);
  std::string line;
  std::getline(in, line);
  if (line.rfind("ref:", 0) == 0) {
    auto ref = trim(line.substr(4));
    std::ifstream ref_in(git / ref);
    std::getline(ref_in, line);
  }
  return trim(line);
}

}  // namespace

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
  if (ext == ".rs") return "rust";
  if (ext == ".js") return "javascript";
  if (ext == ".ts" || ext == ".tsx") return "typescript";
  if (ext == ".go") return "go";
  if (ext == ".md") return "markdown";
  if (ext == ".json") return "json";
  if (ext == ".yaml" || ext == ".yml") return "yaml";
  if (ext == ".toml") return "toml";
  if (ext == ".sh") return "shell";
  if (ext == ".txt" || ext.empty()) return "text";
  return "unknown";
}

int Indexer::index_file(const fs::path &path, std::size_t max_file_bytes) {
  if (!fs::is_regular_file(path) || should_ignore(path)) return 0;
  if (fs::file_size(path) > max_file_bytes) return 0;
  auto content = read_file(path);
  if (content.find('\0') != std::string::npos) return 0;
  auto lang = language_for(path);
  auto filepath = fs::absolute(path).string();

  std::vector<Chunk> chunks;
  if (lang == "markdown") chunks = chunk_markdown(filepath, content);
  else if (lang == "json" || lang == "yaml" || lang == "toml") chunks = chunk_config(filepath, content, lang);
  else chunks = chunk_code(filepath, content, lang);

  auto repo_root = git_root_for(path);
  auto git_head = git_head_for(repo_root);
  int64_t modified_at = 0;
  try {
    auto file_time = fs::last_write_time(path);
    auto system_time = std::chrono::time_point_cast<std::chrono::seconds>(
        file_time - fs::file_time_type::clock::now() + std::chrono::system_clock::now());
    modified_at = system_time.time_since_epoch().count();
  } catch (...) {
    modified_at = 0;
  }

  int count = 0;
  storage_.transaction([&] {
    storage_.mark_file_deleted(filepath);
    for (auto &chunk : chunks) {
      chunk.repo_root = repo_root;
      chunk.git_commit = git_head;
      chunk.modified_at = modified_at;
      storage_.upsert_chunk(chunk);
      ++count;
    }
    for (const auto &todo : todo_engine_.extract(filepath, content)) storage_.add_todo(todo);
  });
  return count;
}

void Indexer::mark_deleted(const fs::path &path) {
  storage_.mark_file_deleted(fs::absolute(path).string());
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
