#include "ragd/config.h"

#include <cstdlib>
#include <nlohmann/json.hpp>

namespace ragd {

namespace {
std::string home() {
  const char *h = std::getenv("HOME");
  return h ? h : ".";
}
}  // namespace

Config Config::defaults() {
  Config cfg;
  cfg.db_path = home() + "/.ragd/ragd.sqlite";
  cfg.index_paths = {home() + "/Dominion/docs", home() + "/Dominion/ragd/docs"};
  return cfg;
}

Config Config::from_args(int argc, char **argv) {
  Config cfg = defaults();
  for (int i = 1; i < argc; ++i) {
    std::string arg = argv[i];
    auto next = [&]() -> std::string { return i + 1 < argc ? argv[++i] : ""; };
    if (arg == "--db") cfg.db_path = next();
    else if (arg == "--host") cfg.host = next();
    else if (arg == "--port") cfg.port = std::stoi(next());
    else if (arg == "--path") cfg.index_paths.push_back(next());
    else if (arg == "--watch") cfg.watch = true;
  }
  return cfg;
}

std::string Config::to_json() const {
  nlohmann::json j;
  j["db_path"] = db_path;
  j["index_paths"] = index_paths;
  j["host"] = host;
  j["port"] = port;
  j["max_file_bytes"] = max_file_bytes;
  j["watch"] = watch;
  return j.dump();
}

}  // namespace ragd
