#include "ragd/mcp_server.h"

#include "ragd/dead_zone.h"
#include "ragd/session_bus.h"
#include "ragd/temporal.h"

#include <nlohmann/json.hpp>

namespace ragd {

static nlohmann::json tool(const std::string &name, const std::string &description) {
  return {{"name", name}, {"description", description}, {"inputSchema", {{"type", "object"}}}};
}

std::string mcp_manifest_json() {
  nlohmann::json j;
  j["name"] = "ragd";
  j["version"] = "0.1.0";
  j["tools"] = {
      tool("ragd_query", "Search indexed project memory."),
      tool("ragd_remember", "Persist an agent decision."),
      tool("ragd_todo_add", "Add a TODO."),
      tool("ragd_todo_list", "List open TODOs."),
      tool("ragd_todo_resolve", "Resolve a TODO."),
      tool("ragd_handoff_read", "Read current handoff context."),
      tool("ragd_handoff_write", "Store a handoff decision."),
      tool("ragd_session_start", "Start an agent session."),
      tool("ragd_broadcast", "Write a session bus message."),
      tool("ragd_deadzone_report", "Report low-context project areas."),
      tool("ragd_temporal_query", "Temporal search status or query."),
  };
  return j.dump();
}

std::string mcp_handle_json(const std::string &body, Storage &storage, RagEngine &rag) {
  nlohmann::json req = nlohmann::json::parse(body.empty() ? "{}" : body, nullptr, false);
  nlohmann::json res;
  res["jsonrpc"] = "2.0";
  res["id"] = req.contains("id") ? req["id"] : nlohmann::json(nullptr);
  auto method = req.value("method", "");
  if (method == "initialize") {
    res["result"] = {{"protocolVersion", "2024-11-05"}, {"serverInfo", {{"name", "ragd"}, {"version", "0.1.0"}}}};
  } else if (method == "tools/list") {
    res["result"] = nlohmann::json::parse(mcp_manifest_json())["tools"];
  } else if (method == "tools/call") {
    auto params = req.value("params", nlohmann::json::object());
    auto name = params.value("name", "");
    auto args = params.value("arguments", nlohmann::json::object());
    if (name == "ragd_query") res["result"] = nlohmann::json::parse(rag.query_json(args.value("query", ""), args.value("mode", "hybrid"), args.value("limit", 10)));
    else if (name == "ragd_remember" || name == "ragd_handoff_write") res["result"] = {{"decision_id", storage.add_decision(args.value("session_id", "mcp"), args.value("text", ""))}};
    else if (name == "ragd_todo_add") {
      Todo t; t.filepath = args.value("filepath", "manual"); t.line = args.value("line", 1); t.tag = args.value("tag", "TODO"); t.text = args.value("text", ""); t.priority = args.value("priority", 5); t.content_hash = sha256ish(t.filepath + t.text);
      res["result"] = {{"todo_id", storage.add_todo(t)}};
    } else if (name == "ragd_todo_list") res["result"] = nlohmann::json::parse(storage.handoff_json())["active_todos"];
    else if (name == "ragd_todo_resolve") { storage.update_todo_status(args.value("id", 0), "resolved"); res["result"] = {{"ok", true}}; }
    else if (name == "ragd_handoff_read") res["result"] = nlohmann::json::parse(storage.handoff_json());
    else if (name == "ragd_session_start") res["result"] = {{"session_id", storage.start_session(args.value("agent", "agent"))}};
    else if (name == "ragd_broadcast") res["result"] = {{"message_id", broadcast(storage, args.value("session_id", "mcp"), args.value("channel", "general"), args.value("message", ""))}};
    else if (name == "ragd_deadzone_report") res["result"] = nlohmann::json::parse(dead_zone_report_json(storage));
    else if (name == "ragd_temporal_query") res["result"] = nlohmann::json::parse(temporal_status_json());
    else res["error"] = {{"code", -32601}, {"message", "unknown tool"}};
  } else {
    res["error"] = {{"code", -32601}, {"message", "unknown method"}};
  }
  return res.dump();
}

}  // namespace ragd
