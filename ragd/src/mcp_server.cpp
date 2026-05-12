#include "ragd/mcp_server.h"

#include "ragd/dead_zone.h"
#include "ragd/session_bus.h"
#include "ragd/temporal.h"

#include <nlohmann/json.hpp>

namespace ragd {

namespace {

nlohmann::json schema(const nlohmann::json &properties, const std::vector<std::string> &required = {}) {
  nlohmann::json s{{"type", "object"}, {"properties", properties}};
  if (!required.empty()) s["required"] = required;
  return s;
}

nlohmann::json tool(const std::string &name, const std::string &description, const nlohmann::json &input_schema) {
  return {{"name", name}, {"description", description}, {"inputSchema", input_schema}};
}

nlohmann::json tools() {
  return nlohmann::json::array({
      tool("ragd_query", "Search the ragd hybrid knowledge base.", schema({{"q", {{"type", "string"}}}, {"top_k", {{"type", "integer"}}}, {"mode", {{"type", "string"}}}, {"lang_filter", {{"type", "array"}, {"items", {{"type", "string"}}}}}}, {"q"})),
      tool("ragd_remember", "Store a fact, decision, note, or warning.", schema({{"kind", {{"type", "string"}, {"enum", {"decision", "note", "warning"}}}}, {"content", {{"type", "string"}}}, {"filepath", {{"type", "string"}}}, {"tags", {{"type", "array"}, {"items", {{"type", "string"}}}}}}, {"kind", "content"})),
      tool("ragd_todo_add", "Add a TODO to the tracker.", schema({{"content", {{"type", "string"}}}, {"kind", {{"type", "string"}}}, {"priority", {{"type", "integer"}}}, {"filepath", {{"type", "string"}}}, {"line", {{"type", "integer"}}}}, {"content"})),
      tool("ragd_todo_list", "List open TODOs.", schema({{"priority_max", {{"type", "integer"}}}, {"kind", {{"type", "string"}}}, {"limit", {{"type", "integer"}}}})),
      tool("ragd_todo_resolve", "Mark a TODO as done.", schema({{"todo_id", {{"type", "integer"}}}, {"resolution_note", {{"type", "string"}}}}, {"todo_id"})),
      tool("ragd_handoff_read", "Read the full project handoff context.", schema({})),
      tool("ragd_handoff_write", "Write a handoff note and close a session.", schema({{"summary", {{"type", "string"}}}, {"handoff_note", {{"type", "string"}}}, {"session_id", {{"type", "string"}}}}, {"summary", "handoff_note", "session_id"})),
      tool("ragd_session_start", "Register a new agent session.", schema({{"agent_name", {{"type", "string"}}}}, {"agent_name"})),
      tool("ragd_temporal_query", "Search with temporal commit context.", schema({{"q", {{"type", "string"}}}, {"git_commit", {{"type", "string"}}}, {"top_k", {{"type", "integer"}}}}, {"q", "git_commit"})),
      tool("ragd_broadcast", "Send a message on the session bus.", schema({{"topic", {{"type", "string"}}}, {"kind", {{"type", "string"}}}, {"message", {{"type", "string"}}}, {"session_id", {{"type", "string"}}}}, {"topic", "kind", "message"})),
      tool("ragd_deadzone_report", "Get orphaned/stale/dead-zone findings.", schema({{"path", {{"type", "string"}}}})),
  });
}

nlohmann::json make_error(const nlohmann::json &id, int code, const std::string &message) {
  return {{"jsonrpc", "2.0"}, {"id", id}, {"error", {{"code", code}, {"message", message}}}};
}

}  // namespace

std::string mcp_manifest_json() {
  nlohmann::json j;
  j["name"] = "ragd";
  j["version"] = "1.0.0";
  j["description"] = "Blackmark Dominion persistent RAG daemon: shared memory, TODOs, handoffs, and retrieval for coding agents.";
  j["tools"] = tools();
  return j.dump();
}

std::string mcp_handle_json(const std::string &body, Storage &storage, RagEngine &rag) {
  nlohmann::json req = nlohmann::json::parse(body.empty() ? "{}" : body, nullptr, false);
  if (req.is_discarded()) return make_error(nullptr, -32700, "invalid JSON").dump();

  nlohmann::json id = req.contains("id") ? req["id"] : nlohmann::json(nullptr);
  nlohmann::json res{{"jsonrpc", "2.0"}, {"id", id}};
  auto method = req.value("method", "");

  if (method == "initialize") {
    res["result"] = {
        {"protocolVersion", "2025-03-26"},
        {"serverInfo", {{"name", "ragd"}, {"version", "1.0.0"}}},
        {"capabilities", {{"tools", nlohmann::json::object()}, {"prompts", nlohmann::json::object()}, {"resources", nlohmann::json::object()}}},
    };
  } else if (method == "tools/list") {
    res["result"] = {{"tools", tools()}};
  } else if (method == "prompts/list") {
    res["result"] = {{"prompts", nlohmann::json::array({{{"name", "ragd_agent_init"}, {"description", "Load ragd handoff context and start a tracked agent session."}}})}};
  } else if (method == "prompts/get") {
    res["result"] = {{"description", "RAGD agent startup prompt"}, {"messages", nlohmann::json::array({{{"role", "user"}, {"content", {{"type", "text"}, {"text", "At session start, call ragd_handoff_read, then ragd_session_start. During work, record important decisions and TODOs. Before ending, call ragd_handoff_write."}}}}})}};
  } else if (method == "resources/list") {
    res["result"] = {{"resources", nlohmann::json::array({{{"uri", "ragd://metrics"}, {"name", "RAGD metrics"}}, {{"uri", "ragd://handoff"}, {"name", "RAGD handoff context"}}, {{"uri", "ragd://sessions/active"}, {"name", "Active sessions"}}})}};
  } else if (method == "tools/call") {
    auto params = req.value("params", nlohmann::json::object());
    auto name = params.value("name", "");
    auto args = params.value("arguments", nlohmann::json::object());
    nlohmann::json result;

    if (name == "ragd_query") {
      result = nlohmann::json::parse(rag.query_json(args.value("q", args.value("query", "")), args.value("mode", "hybrid"), args.value("top_k", args.value("limit", 10))));
    } else if (name == "ragd_remember") {
      auto kind = args.value("kind", "note");
      if (kind == "warning") {
        auto id_msg = broadcast(storage, args.value("session_id", "mcp"), "warnings", args.value("content", ""), "warning", 0);
        result = {{"id", id_msg}, {"stored", true}};
      } else {
        auto id_dec = storage.add_decision(args.value("session_id", "mcp"), args.value("content", ""), args.value("filepath", ""), "", "[]", args.contains("tags") ? args["tags"].dump() : "[]");
        result = {{"id", id_dec}, {"stored", true}};
      }
    } else if (name == "ragd_todo_add") {
      Todo t;
      t.filepath = args.value("filepath", "manual");
      t.line = args.value("line", 1);
      t.tag = args.value("kind", "TODO");
      t.text = args.value("content", "");
      t.priority = args.value("priority", 5);
      t.content_hash = sha256ish(t.filepath + ":" + std::to_string(t.line) + ":" + t.tag + ":" + t.text);
      result = {{"todo_id", storage.add_todo(t)}};
    } else if (name == "ragd_todo_list") {
      result = nlohmann::json::array();
      for (const auto &todo : storage.list_todos_filtered("open", args.value("priority_max", 99), args.value("kind", ""), args.value("limit", 50))) {
        result.push_back({{"todo_id", todo.id}, {"filepath", todo.filepath}, {"line", todo.line}, {"kind", todo.tag}, {"content", todo.text}, {"priority", todo.priority}, {"status", todo.status}});
      }
    } else if (name == "ragd_todo_resolve") {
      storage.update_todo_status(args.value("todo_id", args.value("id", 0)), "done");
      result = {{"ok", true}};
    } else if (name == "ragd_handoff_read") {
      result = nlohmann::json::parse(storage.handoff_json());
    } else if (name == "ragd_handoff_write") {
      storage.end_session(args.value("session_id", ""), args.value("summary", ""), args.value("handoff_note", ""), "completed");
      result = {{"ok", true}};
    } else if (name == "ragd_session_start") {
      result = {{"session_id", storage.start_session(args.value("agent_name", args.value("agent", "agent")))}};
    } else if (name == "ragd_temporal_query") {
      result = nlohmann::json::parse(temporal_query_json(storage, rag, args.value("q", ""), args.value("git_commit", ""), args.value("top_k", 5)));
    } else if (name == "ragd_broadcast") {
      auto id_msg = broadcast(storage, args.value("session_id", "mcp"), args.value("topic", "general"), args.value("message", ""), args.value("kind", "broadcast"), args.value("ttl", 0));
      result = {{"ok", true}, {"message_id", id_msg}};
    } else if (name == "ragd_deadzone_report") {
      result = nlohmann::json::parse(dead_zone_report_json(storage))["dead_zones"];
    } else {
      return make_error(id, -32601, "unknown tool: " + name).dump();
    }
    res["result"] = result;
  } else {
    return make_error(id, -32601, "unknown method: " + method).dump();
  }
  return res.dump();
}

}  // namespace ragd
