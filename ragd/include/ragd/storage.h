#pragma once

#include "ragd/sqlite_compat.h"
#include "ragd/types.h"

#include <functional>
#include <memory>
#include <string>
#include <vector>

namespace ragd {

class Statement {
 public:
  Statement(sqlite3 *db, const std::string &sql);
  ~Statement();
  Statement(const Statement &) = delete;
  Statement &operator=(const Statement &) = delete;

  void bind(int index, const std::string &value);
  void bind(int index, int value);
  void bind(int index, int64_t value);
  void bind(int index, double value);
  void bind_null(int index);
  bool step_row();
  void step_done();
  int64_t column_int64(int index) const;
  int column_int(int index) const;
  double column_double(int index) const;
  std::string column_text(int index) const;

 private:
  sqlite3 *db_ = nullptr;
  sqlite3_stmt *stmt_ = nullptr;
};

class Storage {
 public:
  Storage() = default;
  ~Storage();
  Storage(const Storage &) = delete;
  Storage &operator=(const Storage &) = delete;

  void open(const std::string &path);
  void initialize();
  bool health_check();
  void exec(const std::string &sql);
  void transaction(const std::function<void()> &fn);

  int64_t upsert_chunk(const Chunk &chunk);
  std::vector<QueryResult> search_fts(const std::string &query, int limit);
  std::vector<QueryResult> search_like(const std::string &query, int limit);
  std::vector<Chunk> recent_chunks(int limit);
  Chunk get_chunk(int64_t id);
  void mark_file_deleted(const std::string &filepath);
  int64_t add_todo(const Todo &todo);
  std::vector<Todo> list_todos(const std::string &status = "open", int limit = 100);
  std::vector<Todo> list_todos_filtered(const std::string &status, int priority_max, const std::string &kind, int limit);
  void update_todo_status(int64_t id, const std::string &status);
  void update_todo(int64_t id, const std::string &status, const std::string &assigned_to, int priority);
  std::string start_session(const std::string &agent, const std::string &git_branch = "", const std::string &parent_session = "");
  void end_session(const std::string &session_id, const std::string &summary = "", const std::string &handoff_note = "", const std::string &status = "completed");
  void touch_file(const std::string &session_id, const std::string &filepath, const std::string &action = "analyze", const std::string &note = "");
  int64_t add_decision(const std::string &session_id, const std::string &text, const std::string &filepath = "", const std::string &rationale = "", const std::string &alternatives_json = "[]", const std::string &tags_json = "[]");
  std::vector<Decision> recent_decisions(int limit);
  std::vector<Session> list_sessions(const std::string &status, int limit);
  std::string session_json(const std::string &session_id);
  std::string file_history_json(const std::string &filepath);
  std::string agent_timeline_json(int limit = 100);
  int64_t add_bus_message(const std::string &session_id, const std::string &kind, const std::string &topic, const std::string &payload, int ttl = 0);
  std::string bus_messages_json(const std::string &topic = "", int64_t since_epoch = 0);
  std::string bus_locks_json();
  void upsert_file_lock(const std::string &filepath, const std::string &session_id, const std::string &action);
  int64_t add_dead_zone(const std::string &filepath, const std::string &kind, const std::string &symbol, const std::string &detail, double confidence);
  std::string dead_zones_json(bool acknowledged = false);
  std::string symbols_json(const std::string &root = "", int depth = 3);
  void record_metric(const std::string &key, const std::string &value);
  std::string handoff_json();
  std::string metrics_json();
  sqlite3 *db() { return db_; }

 private:
  sqlite3 *db_ = nullptr;
};

std::string now_utc();
std::string sha256ish(const std::string &input);

}  // namespace ragd
