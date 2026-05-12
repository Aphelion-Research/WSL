#include "ragd/config.h"

#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <nlohmann/json.hpp>
#include <sstream>

namespace ragd {

namespace {

std::string home() {
  const char *h = std::getenv("HOME");
  return h ? h : ".";
}

std::string expand_user(std::string value) {
  if (value == "~") return home();
  if (value.rfind("~/", 0) == 0) return home() + value.substr(1);
  return value;
}

std::vector<std::string> expand_list(const std::vector<std::string> &values) {
  std::vector<std::string> out;
  out.reserve(values.size());
  for (auto value : values) out.push_back(expand_user(std::move(value)));
  return out;
}

std::vector<std::string> split_env_list(const std::string &value) {
  std::vector<std::string> out;
  std::stringstream ss(value);
  std::string item;
  while (std::getline(ss, item, ':')) {
    if (!item.empty()) out.push_back(expand_user(item));
  }
  return out;
}

template <typename T>
void set_if_json(const nlohmann::json &j, const char *key, T &target) {
  if (j.contains(key) && !j[key].is_null()) target = j[key].get<T>();
}

void write_default_config(const std::filesystem::path &path, const Config &cfg) {
  std::filesystem::create_directories(path.parent_path());
  std::ofstream out(path);
  out << cfg.to_json() << "\n";
}

void apply_env(Config &cfg) {
  auto env = [](const char *name) -> const char * { return std::getenv(name); };
  if (auto v = env("RAGD_SERVER_HOST")) cfg.host = v;
  if (auto v = env("RAGD_HOST")) cfg.host = v;
  if (auto v = env("RAGD_SERVER_PORT")) cfg.port = std::stoi(v);
  if (auto v = env("RAGD_PORT")) cfg.port = std::stoi(v);
  if (auto v = env("RAGD_STORAGE_DB_PATH")) cfg.db_path = expand_user(v);
  if (auto v = env("RAGD_DB_PATH")) cfg.db_path = expand_user(v);
  if (auto v = env("RAGD_STORAGE_VECTOR_INDEX_PATH")) cfg.vector_index_path = expand_user(v);
  if (auto v = env("RAGD_INDEXING_WATCH_PATHS")) cfg.index_paths = split_env_list(v);
  if (auto v = env("RAGD_WATCH_PATHS")) cfg.index_paths = split_env_list(v);
  if (auto v = env("RAGD_INDEXING_MAX_FILE_SIZE_MB")) cfg.max_file_bytes = static_cast<std::size_t>(std::stoll(v)) * 1024 * 1024;
  if (auto v = env("RAGD_EMBEDDING_BACKEND")) cfg.embedding_backend = v;
  if (auto v = env("RAGD_EMBED_URL")) cfg.openai_url = v;
  if (auto v = env("RAGD_EMBED_MODEL")) cfg.openai_model = v;
  if (auto v = env("RAGD_LOGGING_LEVEL")) cfg.log_level = v;
}

}  // namespace

Config Config::defaults() {
  Config cfg;
  cfg.db_path = home() + "/.ragd/ragd.db";
  cfg.vector_index_path = home() + "/.ragd/hnsw.bin";
  cfg.log_file = home() + "/.ragd/ragd.log";
  cfg.index_paths = {home() + "/Dominion"};
  cfg.ignore_patterns = {"*.pyc", "__pycache__", "node_modules", ".git", "*.egg-info", "dist/", "build/", "secrets", ".venv", "vendor"};
  cfg.extensions = {".py", ".cpp", ".cc", ".cxx", ".h", ".hpp", ".rs", ".ts", ".js", ".go", ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".sh"};
  return cfg;
}

Config Config::from_file(const std::string &path) {
  Config cfg = defaults();
  auto expanded = std::filesystem::path(expand_user(path));
  if (!std::filesystem::exists(expanded)) {
    write_default_config(expanded, cfg);
    return cfg;
  }

  std::ifstream in(expanded);
  nlohmann::json j = nlohmann::json::parse(in, nullptr, false);
  if (j.is_discarded()) return cfg;

  if (j.contains("server")) {
    const auto &s = j["server"];
    set_if_json(s, "host", cfg.host);
    set_if_json(s, "port", cfg.port);
    set_if_json(s, "unix_socket", cfg.unix_socket);
    set_if_json(s, "max_connections", cfg.max_connections);
    set_if_json(s, "request_timeout_ms", cfg.request_timeout_ms);
  }
  if (j.contains("storage")) {
    const auto &s = j["storage"];
    set_if_json(s, "db_path", cfg.db_path);
    set_if_json(s, "vector_index_path", cfg.vector_index_path);
    set_if_json(s, "embed_dim", cfg.embed_dim);
  }
  if (j.contains("embedding")) {
    const auto &e = j["embedding"];
    set_if_json(e, "backend", cfg.embedding_backend);
    set_if_json(e, "ollama_url", cfg.ollama_url);
    set_if_json(e, "ollama_model", cfg.ollama_model);
    set_if_json(e, "openai_url", cfg.openai_url);
    set_if_json(e, "openai_model", cfg.openai_model);
    set_if_json(e, "openai_key_env", cfg.openai_key_env);
    set_if_json(e, "fallback_to_tfidf", cfg.fallback_to_tfidf);
  }
  if (j.contains("indexing")) {
    const auto &i = j["indexing"];
    if (i.contains("watch_paths")) cfg.index_paths = expand_list(i["watch_paths"].get<std::vector<std::string>>());
    if (i.contains("ignore_patterns")) cfg.ignore_patterns = i["ignore_patterns"].get<std::vector<std::string>>();
    if (i.contains("extensions")) cfg.extensions = i["extensions"].get<std::vector<std::string>>();
    if (i.contains("max_file_size_mb")) cfg.max_file_bytes = static_cast<std::size_t>(i["max_file_size_mb"].get<int>()) * 1024 * 1024;
  }
  if (j.contains("retrieval")) {
    const auto &r = j["retrieval"];
    set_if_json(r, "default_top_k", cfg.default_top_k);
    set_if_json(r, "bm25_candidates", cfg.bm25_candidates);
    set_if_json(r, "vector_candidates", cfg.vector_candidates);
    set_if_json(r, "rrf_k", cfg.rrf_k);
  }
  if (j.contains("temporal")) {
    const auto &t = j["temporal"];
    set_if_json(t, "enabled", cfg.temporal_enabled);
    set_if_json(t, "index_last_n_commits", cfg.temporal_commits);
  }
  if (j.contains("dead_zone")) {
    const auto &d = j["dead_zone"];
    set_if_json(d, "scan_interval_hours", cfg.dead_zone_scan_hours);
    set_if_json(d, "auto_scan_on_startup", cfg.dead_zone_auto_scan);
  }
  if (j.contains("logging")) {
    const auto &l = j["logging"];
    set_if_json(l, "level", cfg.log_level);
    set_if_json(l, "file", cfg.log_file);
  }

  cfg.db_path = expand_user(cfg.db_path);
  cfg.vector_index_path = expand_user(cfg.vector_index_path);
  cfg.log_file = expand_user(cfg.log_file);
  cfg.index_paths = expand_list(cfg.index_paths);
  return cfg;
}

Config Config::from_args(int argc, char **argv) {
  std::string config_path = home() + "/.ragd/config.json";
  for (int i = 1; i < argc; ++i) {
    std::string arg = argv[i];
    if ((arg == "--config" || arg == "-c") && i + 1 < argc) config_path = argv[++i];
  }

  Config cfg = from_file(config_path);
  for (int i = 1; i < argc; ++i) {
    std::string arg = argv[i];
    auto next = [&]() -> std::string { return i + 1 < argc ? argv[++i] : ""; };
    if (arg == "--config" || arg == "-c") {
      (void)next();
    } else if (arg == "--db") {
      cfg.db_path = expand_user(next());
    } else if (arg == "--host") {
      cfg.host = next();
    } else if (arg == "--port") {
      cfg.port = std::stoi(next());
    } else if (arg == "--path") {
      cfg.index_paths.push_back(expand_user(next()));
    } else if (arg == "--watch") {
      cfg.watch = true;
    } else if (arg == "--daemon") {
      cfg.watch = true;
    }
  }
  apply_env(cfg);
  return cfg;
}

std::string Config::to_json() const {
  nlohmann::json j;
  j["server"] = {
      {"host", host},
      {"port", port},
      {"unix_socket", unix_socket},
      {"max_connections", max_connections},
      {"request_timeout_ms", request_timeout_ms},
  };
  j["storage"] = {
      {"db_path", db_path},
      {"vector_index_path", vector_index_path},
      {"embed_dim", embed_dim},
      {"hnsw_M", 16},
      {"hnsw_ef_construction", 200},
  };
  j["embedding"] = {
      {"backend", embedding_backend},
      {"ollama_url", ollama_url},
      {"ollama_model", ollama_model},
      {"openai_url", openai_url},
      {"openai_model", openai_model},
      {"openai_key_env", openai_key_env},
      {"batch_size", 32},
      {"fallback_to_tfidf", fallback_to_tfidf},
  };
  j["indexing"] = {
      {"watch_paths", index_paths},
      {"ignore_patterns", ignore_patterns},
      {"max_file_size_mb", static_cast<int>(max_file_bytes / 1024 / 1024)},
      {"extensions", extensions},
      {"chunk_max_tokens", 512},
      {"chunk_overlap_tokens", 64},
  };
  j["retrieval"] = {
      {"default_top_k", default_top_k},
      {"bm25_candidates", bm25_candidates},
      {"vector_candidates", vector_candidates},
      {"rrf_k", rrf_k},
  };
  j["temporal"] = {{"enabled", temporal_enabled}, {"index_last_n_commits", temporal_commits}};
  j["dead_zone"] = {{"scan_interval_hours", dead_zone_scan_hours}, {"auto_scan_on_startup", dead_zone_auto_scan}};
  j["logging"] = {{"level", log_level}, {"file", log_file}, {"max_size_mb", 100}};
  return j.dump(2);
}

}  // namespace ragd
