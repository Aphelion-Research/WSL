#include "dominion_native/file_classifier.hpp"

#include "dominion_native/path_normalizer.hpp"

#include <algorithm>
#include <array>
#include <cctype>
#include <fstream>
#include <map>

namespace dominion_native {
namespace {

std::string lower(std::string value) {
  std::transform(value.begin(), value.end(), value.begin(), [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
  return value;
}

const std::map<std::string, std::pair<std::string, std::string>> &ext_map() {
  static const std::map<std::string, std::pair<std::string, std::string>> m = {
      {".c", {"source", "c"}},       {".cc", {"source", "cpp"}},       {".cpp", {"source", "cpp"}},
      {".cxx", {"source", "cpp"}},   {".h", {"source", "header"}},     {".hpp", {"source", "header"}},
      {".hxx", {"source", "header"}}, {".py", {"source", "python"}},    {".pyi", {"source", "python"}},
      {".md", {"document", "markdown"}}, {".mdx", {"document", "markdown"}}, {".txt", {"text", "text"}},
      {".json", {"config", "json"}}, {".yaml", {"config", "yaml"}},   {".yml", {"config", "yaml"}},
      {".toml", {"config", "toml"}}, {".cmake", {"build", "cmake"}},  {".sh", {"source", "shell"}},
      {".bash", {"source", "shell"}}, {".sql", {"source", "sql"}},    {".ini", {"config", "ini"}},
      {".cfg", {"config", "ini"}},   {".conf", {"config", "conf"}},   {".xml", {"config", "xml"}},
      {".csv", {"data", "text"}},    {".tsv", {"data", "text"}},      {".jsonl", {"data", "json"}},
  };
  return m;
}

const std::map<std::string, std::pair<std::string, std::string>> &name_map() {
  static const std::map<std::string, std::pair<std::string, std::string>> m = {
      {"CMakeLists.txt", {"build", "cmake"}},
      {"Makefile", {"build", "makefile"}},
      {"Dockerfile", {"config", "dockerfile"}},
      {"AGENTS.md", {"document", "markdown"}},
      {"README", {"document", "text"}},
      {"LICENSE", {"document", "text"}},
  };
  return m;
}

bool generated_path(const std::string &relative) {
  const auto p = "/" + relative + "/";
  const char *dirs[] = {"/build/", "/vendor/", "/__pycache__/", "/.pytest_cache/", "/.mypy_cache/", "/.ruff_cache/", "/vault/", "/.git/"};
  for (const auto *dir : dirs) {
    if (p.find(dir) != std::string::npos) return true;
  }
  return false;
}

bool sample_is_binary(const std::filesystem::path &path) {
  std::ifstream in(path, std::ios::binary);
  if (!in) return true;
  std::array<unsigned char, 8192> buffer{};
  in.read(reinterpret_cast<char *>(buffer.data()), static_cast<std::streamsize>(buffer.size()));
  const auto n = static_cast<std::size_t>(in.gcount());
  if (n == 0) return false;
  std::size_t suspicious = 0;
  for (std::size_t i = 0; i < n; ++i) {
    const auto ch = buffer[i];
    if (ch == 0) return true;
    if (ch < 7 || (ch > 13 && ch < 32)) ++suspicious;
  }
  return (static_cast<double>(suspicious) / static_cast<double>(n)) > 0.30;
}

}  // namespace

nlohmann::json FileClassification::to_json() const {
  return {
      {"path", path},
      {"kind", kind},
      {"language", language},
      {"binary", binary},
      {"text", text},
      {"encoding", encoding},
      {"large", large},
      {"generated", generated},
      {"reason", reason},
  };
}

FileClassification classify_file(const std::filesystem::path &absolute_path, const std::string &relative_path, std::uintmax_t size_bytes, std::size_t large_threshold) {
  FileClassification out;
  out.path = relative_path;
  out.large = large_threshold > 0 && size_bytes > large_threshold;
  out.generated = generated_path(relative_path);

  const auto name = absolute_path.filename().generic_string();
  auto n = name_map().find(name);
  if (n != name_map().end()) {
    out.kind = n->second.first;
    out.language = n->second.second;
    out.reason = "name:" + name;
  } else {
    const auto ext = lower(absolute_path.extension().generic_string());
    auto e = ext_map().find(ext);
    if (e != ext_map().end()) {
      out.kind = e->second.first;
      out.language = e->second.second;
      out.reason = "extension:" + ext;
    }
  }

  out.binary = sample_is_binary(absolute_path);
  out.text = !out.binary;
  if (out.binary) {
    out.kind = "binary";
    out.language = "unknown";
    out.encoding = "binary";
    if (out.reason == "unknown") out.reason = "binary_sample";
  }
  return out;
}

}  // namespace dominion_native

