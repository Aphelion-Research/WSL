#include "ragd/http_api.h"

#include "ragd/mcp_server.h"

#include <httplib.h>
#include <nlohmann/json.hpp>

namespace ragd {

HttpApi::HttpApi(Config config, Storage &storage, Indexer &indexer, RagEngine &rag)
    : config_(std::move(config)), storage_(storage), indexer_(indexer), rag_(rag) {}

void HttpApi::run() {
  httplib::Server server;
  auto json = [](httplib::Response &res, const std::string &body) { res.set_content(body, "application/json"); };
  server.Get("/health", [&](const httplib::Request &, httplib::Response &res) {
    nlohmann::json j{{"ok", storage_.health_check()}, {"metrics", nlohmann::json::parse(storage_.metrics_json())}};
    json(res, j.dump());
  });
  server.Post("/index", [&](const httplib::Request &req, httplib::Response &res) {
    auto body = nlohmann::json::parse(req.body.empty() ? "{}" : req.body, nullptr, false);
    std::vector<std::string> paths = config_.index_paths;
    if (body.contains("paths")) paths = body["paths"].get<std::vector<std::string>>();
    int chunks = indexer_.index_paths(paths, config_.max_file_bytes);
    json(res, nlohmann::json{{"chunks_indexed", chunks}}.dump());
  });
  server.Post("/query", [&](const httplib::Request &req, httplib::Response &res) {
    auto body = nlohmann::json::parse(req.body.empty() ? "{}" : req.body, nullptr, false);
    json(res, rag_.query_json(body.value("query", ""), body.value("mode", "hybrid"), body.value("limit", 10)));
  });
  server.Get("/handoff", [&](const httplib::Request &, httplib::Response &res) { json(res, storage_.handoff_json()); });
  server.Post("/session/start", [&](const httplib::Request &req, httplib::Response &res) {
    auto body = nlohmann::json::parse(req.body.empty() ? "{}" : req.body, nullptr, false);
    json(res, nlohmann::json{{"session_id", storage_.start_session(body.value("agent", "agent"))}}.dump());
  });
  server.Post("/session/end", [&](const httplib::Request &req, httplib::Response &res) {
    auto body = nlohmann::json::parse(req.body.empty() ? "{}" : req.body, nullptr, false);
    storage_.end_session(body.value("session_id", ""));
    json(res, R"({"ok":true})");
  });
  server.Post("/session/touch", [&](const httplib::Request &req, httplib::Response &res) {
    auto body = nlohmann::json::parse(req.body.empty() ? "{}" : req.body, nullptr, false);
    storage_.touch_file(body.value("session_id", ""), body.value("filepath", ""));
    json(res, R"({"ok":true})");
  });
  server.Post("/memory/decision", [&](const httplib::Request &req, httplib::Response &res) {
    auto body = nlohmann::json::parse(req.body.empty() ? "{}" : req.body, nullptr, false);
    json(res, nlohmann::json{{"decision_id", storage_.add_decision(body.value("session_id", ""), body.value("text", ""))}}.dump());
  });
  server.Get("/memory/decisions", [&](const httplib::Request &, httplib::Response &res) {
    nlohmann::json j = nlohmann::json::array();
    for (auto &d : storage_.recent_decisions(50)) j.push_back({{"id", d.id}, {"session_id", d.session_id}, {"text", d.text}, {"created_at", d.created_at}});
    json(res, j.dump());
  });
  server.Get("/todos", [&](const httplib::Request &, httplib::Response &res) { json(res, storage_.handoff_json()); });
  server.Post("/todos", [&](const httplib::Request &req, httplib::Response &res) {
    auto body = nlohmann::json::parse(req.body.empty() ? "{}" : req.body, nullptr, false);
    Todo t; t.filepath = body.value("filepath", "manual"); t.line = body.value("line", 1); t.tag = body.value("tag", "TODO"); t.text = body.value("text", ""); t.priority = body.value("priority", 5); t.content_hash = sha256ish(t.filepath + t.text);
    json(res, nlohmann::json{{"todo_id", storage_.add_todo(t)}}.dump());
  });
  server.Get("/todos/search", [&](const httplib::Request &req, httplib::Response &res) { json(res, rag_.query_json(req.get_param_value("q"), "bm25", 10)); });
  server.Get("/metrics", [&](const httplib::Request &, httplib::Response &res) { json(res, storage_.metrics_json()); });
  server.Get("/mcp", [&](const httplib::Request &, httplib::Response &res) { json(res, mcp_manifest_json()); });
  server.Post("/mcp", [&](const httplib::Request &req, httplib::Response &res) { json(res, mcp_handle_json(req.body, storage_, rag_)); });
  server.listen(config_.host, config_.port);
}

}  // namespace ragd
