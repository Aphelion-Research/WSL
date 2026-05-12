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
  std::vector<Chunk> recent_chunks(int limit);
  int64_t add_todo(const Todo &todo);
  std::vector<Todo> list_todos(const std::string &status = "open", int limit = 100);
  void update_todo_status(int64_t id, const std::string &status);
  std::string start_session(const std::string &agent);
  void end_session(const std::string &session_id);
  void touch_file(const std::string &session_id, const std::string &filepath);
  int64_t add_decision(const std::string &session_id, const std::string &text);
  std::vector<Decision> recent_decisions(int limit);
  int64_t add_bus_message(const std::string &session_id, const std::string &channel, const std::string &message);
  std::string handoff_json();
  std::string metrics_json();
  sqlite3 *db() { return db_; }

 private:
  sqlite3 *db_ = nullptr;
};

std::string now_utc();
std::string sha256ish(const std::string &input);

}  // namespace ragd
