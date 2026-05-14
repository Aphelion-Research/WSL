#include "ragd/http_api.h"

#include "ragd/dead_zone.h"
#include "ragd/mcp_server.h"
#include "ragd/session_bus.h"
#include "ragd/temporal.h"

#include <httplib.h>
#include <nlohmann/json.hpp>

#include <filesystem>

namespace ragd {

namespace {

nlohmann::json parse_body(const httplib::Request &req) {
  auto body = nlohmann::json::parse(req.body.empty() ? "{}" : req.body, nullptr, false);
  return body.is_discarded() ? nlohmann::json::object() : body;
}

void json_response(httplib::Response &res, const nlohmann::json &body, int status = 200) {
  res.status = status;
  res.set_content(body.dump(), "application/json");
}

void json_response(httplib::Response &res, const std::string &body, int status = 200) {
  res.status = status;
  res.set_content(body, "application/json");
}

int int_param(const httplib::Request &req, const std::string &name, int fallback) {
  if (!req.has_param(name)) return fallback;
  try {
    return std::stoi(req.get_param_value(name));
  } catch (...) {
    return fallback;
  }
}

int64_t int64_param(const httplib::Request &req, const std::string &name, int64_t fallback) {
  if (!req.has_param(name)) return fallback;
  try {
    return std::stoll(req.get_param_value(name));
  } catch (...) {
    return fallback;
  }
}

Todo todo_from_json(const nlohmann::json &body) {
  Todo t;
  t.filepath = body.value("filepath", "manual");
  t.line = body.value("line_number", body.value("line", 1));
  t.tag = body.value("kind", body.value("tag", "TODO"));
  t.text = body.value("content", body.value("text", ""));
  t.priority = body.value("priority", 5);
  t.status = body.value("status", "open");
  t.assigned_to = body.value("assigned_to", "");
  t.symbol_name = body.value("symbol_name", "");
  if (body.contains("tags")) t.tags_json = body["tags"].dump();
  t.content_hash = sha256ish(t.filepath + ":" + std::to_string(t.line) + ":" + t.tag + ":" + t.text);
  return t;
}

nlohmann::json todo_json(const Todo &todo) {
  return {
      {"id", todo.id},
      {"todo_id", todo.id},
      {"filepath", todo.filepath},
      {"line_number", todo.line},
      {"kind", todo.tag},
      {"content", todo.text},
      {"priority", todo.priority},
      {"status", todo.status},
      {"assigned_to", todo.assigned_to},
      {"symbol_name", todo.symbol_name},
  };
}

}  // namespace

HttpApi::HttpApi(Config config, Storage &storage, Indexer &indexer, RagEngine &rag)
    : config_(std::move(config)), storage_(storage), indexer_(indexer), rag_(rag) {}

void HttpApi::run() {
  httplib::Server server;
  server.set_exception_handler([](const httplib::Request &, httplib::Response &res, std::exception_ptr ep) {
    std::string message = "unknown error";
    try {
      if (ep) std::rethrow_exception(ep);
    } catch (const std::exception &e) {
      message = e.what();
    }
    json_response(res, nlohmann::json{{"error", message}, {"code", 500}}, 500);
  });

  server.Get("/health", [&](const httplib::Request &, httplib::Response &res) {
    auto metrics = nlohmann::json::parse(storage_.metrics_json());
    metrics["ok"] = storage_.health_check();
    metrics["status"] = storage_.health_check() ? "ok" : "error";
    json_response(res, metrics);
  });

  server.Post("/index", [&](const httplib::Request &req, httplib::Response &res) {
    auto body = parse_body(req);
    std::vector<std::string> paths = config_.index_paths;
    if (body.contains("paths") && body["paths"].is_array()) paths = body["paths"].get<std::vector<std::string>>();
    if (body.contains("path") && body["path"].is_string()) paths = {body["path"].get<std::string>()};
    int chunks = indexer_.index_paths(paths, config_.max_file_bytes);
    json_response(res, nlohmann::json{{"queued", chunks}, {"chunks_indexed", chunks}, {"already_current", 0}});
  });

  server.Post("/index/delete", [&](const httplib::Request &req, httplib::Response &res) {
    auto body = parse_body(req);
    std::vector<std::string> paths;
    if (body.contains("paths") && body["paths"].is_array()) paths = body["paths"].get<std::vector<std::string>>();
    if (body.contains("path") && body["path"].is_string()) paths = {body["path"].get<std::string>()};

    int files_marked_deleted = 0;
    int chunks_marked_deleted = 0;
    nlohmann::json errors = nlohmann::json::array();
    for (const auto &path : paths) {
      if (path.empty()) {
        errors.push_back({{"path", path}, {"error", "empty path"}});
        continue;
      }
      try {
        auto absolute = std::filesystem::absolute(path).string();
        int deleted = storage_.mark_file_deleted(absolute);
        if (deleted > 0) ++files_marked_deleted;
        chunks_marked_deleted += deleted;
      } catch (const std::exception &e) {
        errors.push_back({{"path", path}, {"error", e.what()}});
      }
    }

    json_response(res, nlohmann::json{
                           {"ok", errors.empty()},
                           {"paths_submitted", paths.size()},
                           {"files_marked_deleted", files_marked_deleted},
                           {"chunks_marked_deleted", chunks_marked_deleted},
                           {"errors", errors},
                       },
                  errors.empty() ? 200 : 400);
  });

  server.Post("/query", [&](const httplib::Request &req, httplib::Response &res) {
    auto body = parse_body(req);
    std::string q = body.value("q", body.value("query", ""));
    std::string mode = body.value("mode", "hybrid");
    int top_k = body.value("top_k", body.value("limit", config_.default_top_k));
    json_response(res, rag_.query_json(q, mode, top_k));
  });

  server.Get("/handoff", [&](const httplib::Request &, httplib::Response &res) { json_response(res, storage_.handoff_json()); });

  server.Post("/session/start", [&](const httplib::Request &req, httplib::Response &res) {
    auto body = parse_body(req);
    auto id = storage_.start_session(body.value("agent_name", body.value("agent", "agent")), body.value("git_branch", ""), body.value("parent_session", ""));
    json_response(res, nlohmann::json{{"session_id", id}, {"started_at", now_utc()}});
  });

  server.Post("/session/end", [&](const httplib::Request &req, httplib::Response &res) {
    auto body = parse_body(req);
    storage_.end_session(body.value("session_id", ""), body.value("summary", ""), body.value("handoff_note", ""), body.value("status", "completed"));
    json_response(res, nlohmann::json{{"ok", true}});
  });

  server.Get("/session/active", [&](const httplib::Request &, httplib::Response &res) {
    nlohmann::json j;
    j["sessions"] = nlohmann::json::array();
    for (const auto &s : storage_.list_sessions("active", 100)) {
      j["sessions"].push_back({{"session_id", s.id}, {"agent_name", s.agent}, {"started_at", s.started_at}, {"status", s.status}, {"git_branch", s.git_branch}});
    }
    json_response(res, j);
  });

  server.Get(R"(/session/(.+))", [&](const httplib::Request &req, httplib::Response &res) {
    json_response(res, storage_.session_json(req.matches[1]));
  });

  server.Post("/session/touch", [&](const httplib::Request &req, httplib::Response &res) {
    auto body = parse_body(req);
    storage_.touch_file(body.value("session_id", ""), body.value("filepath", ""), body.value("action", "analyze"), body.value("note", ""));
    json_response(res, nlohmann::json{{"ok", true}});
  });

  server.Post("/memory/decision", [&](const httplib::Request &req, httplib::Response &res) {
    auto body = parse_body(req);
    auto id = storage_.add_decision(body.value("session_id", ""), body.value("decision", body.value("text", "")), body.value("filepath", ""), body.value("rationale", ""), body.contains("alternatives") ? body["alternatives"].dump() : "[]", body.contains("tags") ? body["tags"].dump() : "[]");
    json_response(res, nlohmann::json{{"id", id}, {"decision_id", id}, {"stored", true}});
  });

  server.Get("/memory/decisions", [&](const httplib::Request &req, httplib::Response &res) {
    int limit = int_param(req, "limit", 20);
    nlohmann::json j;
    j["decisions"] = nlohmann::json::array();
    for (const auto &d : storage_.recent_decisions(limit)) {
      j["decisions"].push_back({{"id", d.id}, {"session_id", d.session_id}, {"filepath", d.filepath}, {"decision", d.text}, {"rationale", d.rationale}, {"created_at", d.created_at}});
    }
    json_response(res, j);
  });

  server.Get("/todos", [&](const httplib::Request &req, httplib::Response &res) {
    auto status = req.has_param("status") ? req.get_param_value("status") : "open";
    auto kind = req.has_param("kind") ? req.get_param_value("kind") : "";
    int priority = int_param(req, "priority", 99);
    int limit = int_param(req, "limit", 50);
    nlohmann::json j;
    j["todos"] = nlohmann::json::array();
    for (const auto &todo : storage_.list_todos_filtered(status, priority, kind, limit)) j["todos"].push_back(todo_json(todo));
    json_response(res, j);
  });

  server.Post("/todos", [&](const httplib::Request &req, httplib::Response &res) {
    Todo t = todo_from_json(parse_body(req));
    auto id = storage_.add_todo(t);
    json_response(res, nlohmann::json{{"todo_id", id}});
  });

  server.Patch(R"(/todos/(\d+))", [&](const httplib::Request &req, httplib::Response &res) {
    auto body = parse_body(req);
    int64_t id = std::stoll(req.matches[1]);
    storage_.update_todo(id, body.value("status", ""), body.value("assigned_to", ""), body.value("priority", 0));
    json_response(res, nlohmann::json{{"ok", true}});
  });

  server.Get("/todos/search", [&](const httplib::Request &req, httplib::Response &res) {
    auto q = req.has_param("q") ? req.get_param_value("q") : "";
    json_response(res, rag_.query_json(q, "hybrid", int_param(req, "limit", 10)));
  });

  server.Get("/metrics", [&](const httplib::Request &, httplib::Response &res) { json_response(res, storage_.metrics_json()); });

  server.Get("/temporal/commits", [&](const httplib::Request &req, httplib::Response &res) {
    json_response(res, temporal_commits_json(storage_, int_param(req, "limit", 20)));
  });
  server.Post("/temporal/query", [&](const httplib::Request &req, httplib::Response &res) {
    auto body = parse_body(req);
    json_response(res, temporal_query_json(storage_, rag_, body.value("q", body.value("query", "")), body.value("git_commit", ""), body.value("top_k", 5)));
  });
  server.Get("/temporal/file-timeline", [&](const httplib::Request &req, httplib::Response &res) {
    json_response(res, temporal_file_timeline_json(storage_, req.has_param("filepath") ? req.get_param_value("filepath") : ""));
  });
  server.Get("/temporal/diff", [&](const httplib::Request &, httplib::Response &res) {
    json_response(res, nlohmann::json{{"diff", nlohmann::json::array()}, {"mode", "chunk_history"}, {"note", "semantic chunk diff requires two recorded versions"}});
  });
  server.Get("/temporal/chunk-diff", [&](const httplib::Request &, httplib::Response &res) {
    json_response(res, nlohmann::json{{"diff", nlohmann::json::array()}, {"mode", "chunk_history"}});
  });

  server.Post("/deadzone/scan", [&](const httplib::Request &req, httplib::Response &res) {
    auto body = parse_body(req);
    auto report = nlohmann::json::parse(dead_zone_report_json(storage_));
    int stored = 0;
    for (const auto &dz : report["dead_zones"]) {
      storage_.add_dead_zone(dz.value("filepath", body.value("path", "")), dz.value("kind", "dead_zone"), dz.value("symbol_name", ""), dz.value("detail", ""), dz.value("confidence", 0.5));
      ++stored;
    }
    json_response(res, nlohmann::json{{"job_id", "inline"}, {"status", "completed"}, {"stored", stored}});
  });
  server.Get("/deadzone/results", [&](const httplib::Request &req, httplib::Response &res) {
    bool ack = req.has_param("acknowledged") && req.get_param_value("acknowledged") == "true";
    json_response(res, storage_.dead_zones_json(ack));
  });

  server.Get("/bus/locks", [&](const httplib::Request &, httplib::Response &res) { json_response(res, storage_.bus_locks_json()); });
  server.Get("/bus/messages", [&](const httplib::Request &req, httplib::Response &res) {
    json_response(res, storage_.bus_messages_json(req.has_param("topic") ? req.get_param_value("topic") : "", int64_param(req, "since", 0)));
  });
  server.Post("/bus/publish", [&](const httplib::Request &req, httplib::Response &res) {
    auto body = parse_body(req);
    nlohmann::json payload = body.contains("payload") ? body["payload"] : nlohmann::json{{"message", body.value("message", "")}};
    auto id = storage_.add_bus_message(body.value("session_id", ""), body.value("kind", "broadcast"), body.value("topic", "general"), payload.dump(), body.value("ttl", 0));
    json_response(res, nlohmann::json{{"ok", true}, {"message_id", id}});
  });

  server.Get(R"(/graph/file-history/(.+))", [&](const httplib::Request &req, httplib::Response &res) {
    json_response(res, storage_.file_history_json(req.matches[1]));
  });
  server.Get(R"(/graph/decision-chain/(.+))", [&](const httplib::Request &req, httplib::Response &res) {
    json_response(res, nlohmann::json{{"chunk_id", req.matches[1]}, {"decisions", nlohmann::json::array()}});
  });
  server.Get(R"(/graph/todo-blockers/(.+))", [&](const httplib::Request &req, httplib::Response &res) {
    json_response(res, nlohmann::json{{"todo_id", req.matches[1]}, {"blockers", nlohmann::json::array()}});
  });
  server.Get("/graph/agent-timeline", [&](const httplib::Request &, httplib::Response &res) { json_response(res, storage_.agent_timeline_json()); });
  server.Get("/graph/symbols", [&](const httplib::Request &req, httplib::Response &res) {
    json_response(res, storage_.symbols_json(req.has_param("root") ? req.get_param_value("root") : "", int_param(req, "depth", 3)));
  });

  server.Get("/mcp", [&](const httplib::Request &, httplib::Response &res) { json_response(res, mcp_manifest_json()); });
  server.Post("/mcp", [&](const httplib::Request &req, httplib::Response &res) { json_response(res, mcp_handle_json(req.body, storage_, rag_)); });

  server.listen(config_.host, config_.port);
}

}  // namespace ragd
