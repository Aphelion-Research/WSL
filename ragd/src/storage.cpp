#include "ragd/storage.h"

#include <chrono>
#include <iomanip>
#include <nlohmann/json.hpp>
#include <sstream>
#include <stdexcept>

namespace ragd {

namespace {

void throw_sqlite(sqlite3 *db, const std::string &context) {
  throw std::runtime_error(context + ": " + (db ? sqlite3_errmsg(db) : "no db"));
}

std::string text_or_empty(const unsigned char *text) {
  return text ? reinterpret_cast<const char *>(text) : "";
}

}  // namespace

std::string now_utc() {
  auto now = std::chrono::system_clock::now();
  auto t = std::chrono::system_clock::to_time_t(now);
  std::tm tm{};
  gmtime_r(&t, &tm);
  std::ostringstream out;
  out << std::put_time(&tm, "%Y-%m-%dT%H:%M:%SZ");
  return out.str();
}

std::string sha256ish(const std::string &input) {
  std::hash<std::string> h;
  std::ostringstream out;
  out << std::hex << h(input);
  return out.str();
}

Statement::Statement(sqlite3 *db, const std::string &sql) : db_(db) {
  if (sqlite3_prepare_v2(db_, sql.c_str(), -1, &stmt_, nullptr) != SQLITE_OK) {
    throw_sqlite(db_, "prepare failed");
  }
}

Statement::~Statement() {
  if (stmt_) sqlite3_finalize(stmt_);
}

void Statement::bind(int index, const std::string &value) {
  if (sqlite3_bind_text(stmt_, index, value.c_str(), static_cast<int>(value.size()), RAGD_SQLITE_TRANSIENT) != SQLITE_OK) throw_sqlite(db_, "bind text failed");
}

void Statement::bind(int index, int value) {
  if (sqlite3_bind_int(stmt_, index, value) != SQLITE_OK) throw_sqlite(db_, "bind int failed");
}

void Statement::bind(int index, int64_t value) {
  if (sqlite3_bind_int64(stmt_, index, value) != SQLITE_OK) throw_sqlite(db_, "bind int64 failed");
}

void Statement::bind(int index, double value) {
  if (sqlite3_bind_double(stmt_, index, value) != SQLITE_OK) throw_sqlite(db_, "bind double failed");
}

bool Statement::step_row() {
  int rc = sqlite3_step(stmt_);
  if (rc == SQLITE_ROW) return true;
  if (rc == SQLITE_DONE) return false;
  throw_sqlite(db_, "step failed");
  return false;
}

void Statement::step_done() {
  int rc = sqlite3_step(stmt_);
  if (rc != SQLITE_DONE) throw_sqlite(db_, "step done failed");
}

int64_t Statement::column_int64(int index) const { return sqlite3_column_int64(stmt_, index); }
int Statement::column_int(int index) const { return sqlite3_column_int(stmt_, index); }
double Statement::column_double(int index) const { return sqlite3_column_double(stmt_, index); }
std::string Statement::column_text(int index) const { return text_or_empty(sqlite3_column_text(stmt_, index)); }

Storage::~Storage() {
  if (db_) sqlite3_close(db_);
}

void Storage::open(const std::string &path) {
  if (sqlite3_open(path.c_str(), &db_) != SQLITE_OK) throw_sqlite(db_, "open failed");
}

void Storage::exec(const std::string &sql) {
  char *err = nullptr;
  int rc = sqlite3_exec(db_, sql.c_str(), nullptr, nullptr, &err);
  if (rc != SQLITE_OK) {
    std::string msg = err ? err : "unknown sqlite error";
    if (err) sqlite3_free(err);
    throw std::runtime_error("sqlite exec failed: " + msg);
  }
}

void Storage::initialize() {
  exec("PRAGMA journal_mode=WAL;");
  exec("PRAGMA synchronous=NORMAL;");
  exec("CREATE TABLE IF NOT EXISTS kv_store(key TEXT PRIMARY KEY, value TEXT NOT NULL);");
  exec("INSERT OR REPLACE INTO kv_store(key,value) VALUES('schema_version','1');");
  exec("CREATE TABLE IF NOT EXISTS chunks(id INTEGER PRIMARY KEY AUTOINCREMENT, filepath TEXT NOT NULL, content TEXT NOT NULL, lang TEXT, chunk_type TEXT, symbol_name TEXT, line_start INTEGER, line_end INTEGER, content_hash TEXT, metadata_json TEXT DEFAULT '{}', status TEXT DEFAULT 'active', updated_at TEXT DEFAULT CURRENT_TIMESTAMP);");
  exec("CREATE VIRTUAL TABLE IF NOT EXISTS fts_chunks USING fts5(content, filepath, chunk_id UNINDEXED);");
  exec("CREATE TABLE IF NOT EXISTS agent_sessions(id TEXT PRIMARY KEY, agent TEXT, started_at TEXT, ended_at TEXT, status TEXT);");
  exec("CREATE TABLE IF NOT EXISTS session_file_touches(id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, filepath TEXT, touched_at TEXT);");
  exec("CREATE TABLE IF NOT EXISTS decisions(id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, text TEXT, created_at TEXT);");
  exec("CREATE TABLE IF NOT EXISTS todos(id INTEGER PRIMARY KEY AUTOINCREMENT, filepath TEXT, line INTEGER, tag TEXT, text TEXT, priority INTEGER, status TEXT DEFAULT 'open', content_hash TEXT UNIQUE, created_at TEXT, updated_at TEXT);");
  exec("CREATE TABLE IF NOT EXISTS bus_messages(id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, channel TEXT, message TEXT, created_at TEXT);");
  exec("CREATE TABLE IF NOT EXISTS dead_zones(id INTEGER PRIMARY KEY AUTOINCREMENT, filepath TEXT, reason TEXT, severity INTEGER, created_at TEXT);");
  exec("CREATE TABLE IF NOT EXISTS chunk_history(id INTEGER PRIMARY KEY AUTOINCREMENT, chunk_id INTEGER, event TEXT, created_at TEXT);");
}

bool Storage::health_check() {
  Statement stmt(db_, "SELECT value FROM kv_store WHERE key='schema_version'");
  return stmt.step_row();
}

void Storage::transaction(const std::function<void()> &fn) {
  exec("BEGIN IMMEDIATE");
  try {
    fn();
    exec("COMMIT");
  } catch (...) {
    exec("ROLLBACK");
    throw;
  }
}

int64_t Storage::upsert_chunk(const Chunk &chunk) {
  Statement stmt(db_, "INSERT INTO chunks(filepath,content,lang,chunk_type,symbol_name,line_start,line_end,content_hash,metadata_json,status,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)");
  stmt.bind(1, chunk.filepath);
  stmt.bind(2, chunk.content);
  stmt.bind(3, chunk.lang);
  stmt.bind(4, chunk.chunk_type);
  stmt.bind(5, chunk.symbol_name);
  stmt.bind(6, chunk.line_start);
  stmt.bind(7, chunk.line_end);
  stmt.bind(8, chunk.content_hash);
  stmt.bind(9, chunk.metadata_json);
  stmt.bind(10, chunk.status);
  stmt.bind(11, now_utc());
  stmt.step_done();
  int64_t id = sqlite3_last_insert_rowid(db_);
  Statement fts(db_, "INSERT INTO fts_chunks(content, filepath, chunk_id) VALUES(?,?,?)");
  fts.bind(1, chunk.content);
  fts.bind(2, chunk.filepath);
  fts.bind(3, id);
  fts.step_done();
  return id;
}

std::vector<QueryResult> Storage::search_fts(const std::string &query, int limit) {
  std::vector<QueryResult> out;
  Statement stmt(db_, "SELECT c.id,c.filepath,c.content,-bm25(fts_chunks),c.lang,c.chunk_type,c.symbol_name,c.line_start,c.line_end FROM fts_chunks JOIN chunks c ON c.id=fts_chunks.chunk_id WHERE fts_chunks MATCH ? AND c.status='active' ORDER BY bm25(fts_chunks) LIMIT ?");
  stmt.bind(1, query);
  stmt.bind(2, limit);
  while (stmt.step_row()) {
    QueryResult r;
    r.chunk_id = stmt.column_int64(0);
    r.filepath = stmt.column_text(1);
    r.content = stmt.column_text(2);
    r.bm25_score = stmt.column_double(3);
    r.score = r.bm25_score;
    r.lang = stmt.column_text(4);
    r.chunk_type = stmt.column_text(5);
    r.symbol_name = stmt.column_text(6);
    r.line_start = stmt.column_int(7);
    r.line_end = stmt.column_int(8);
    out.push_back(std::move(r));
  }
  return out;
}

std::vector<Chunk> Storage::recent_chunks(int limit) {
  std::vector<Chunk> out;
  Statement stmt(db_, "SELECT id,filepath,content,lang,chunk_type,symbol_name,line_start,line_end,content_hash,metadata_json,status FROM chunks WHERE status='active' ORDER BY id DESC LIMIT ?");
  stmt.bind(1, limit);
  while (stmt.step_row()) {
    Chunk c;
    c.id = stmt.column_int64(0);
    c.filepath = stmt.column_text(1);
    c.content = stmt.column_text(2);
    c.lang = stmt.column_text(3);
    c.chunk_type = stmt.column_text(4);
    c.symbol_name = stmt.column_text(5);
    c.line_start = stmt.column_int(6);
    c.line_end = stmt.column_int(7);
    c.content_hash = stmt.column_text(8);
    c.metadata_json = stmt.column_text(9);
    c.status = stmt.column_text(10);
    out.push_back(std::move(c));
  }
  return out;
}

int64_t Storage::add_todo(const Todo &todo) {
  Statement stmt(db_, "INSERT OR IGNORE INTO todos(filepath,line,tag,text,priority,status,content_hash,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)");
  stmt.bind(1, todo.filepath);
  stmt.bind(2, todo.line);
  stmt.bind(3, todo.tag);
  stmt.bind(4, todo.text);
  stmt.bind(5, todo.priority);
  stmt.bind(6, todo.status);
  stmt.bind(7, todo.content_hash);
  auto ts = now_utc();
  stmt.bind(8, ts);
  stmt.bind(9, ts);
  stmt.step_done();
  return sqlite3_last_insert_rowid(db_);
}

std::vector<Todo> Storage::list_todos(const std::string &status, int limit) {
  std::vector<Todo> out;
  Statement stmt(db_, "SELECT id,filepath,line,tag,text,priority,status,content_hash FROM todos WHERE status=? ORDER BY priority ASC,id DESC LIMIT ?");
  stmt.bind(1, status);
  stmt.bind(2, limit);
  while (stmt.step_row()) {
    Todo t;
    t.id = stmt.column_int64(0);
    t.filepath = stmt.column_text(1);
    t.line = stmt.column_int(2);
    t.tag = stmt.column_text(3);
    t.text = stmt.column_text(4);
    t.priority = stmt.column_int(5);
    t.status = stmt.column_text(6);
    t.content_hash = stmt.column_text(7);
    out.push_back(std::move(t));
  }
  return out;
}

void Storage::update_todo_status(int64_t id, const std::string &status) {
  Statement stmt(db_, "UPDATE todos SET status=?, updated_at=? WHERE id=?");
  stmt.bind(1, status);
  stmt.bind(2, now_utc());
  stmt.bind(3, id);
  stmt.step_done();
}

std::string Storage::start_session(const std::string &agent) {
  std::string id = agent + "-" + sha256ish(agent + now_utc()).substr(0, 10);
  Statement stmt(db_, "INSERT INTO agent_sessions(id,agent,started_at,status) VALUES(?,?,?,?)");
  stmt.bind(1, id);
  stmt.bind(2, agent);
  stmt.bind(3, now_utc());
  stmt.bind(4, "active");
  stmt.step_done();
  return id;
}

void Storage::end_session(const std::string &session_id) {
  Statement stmt(db_, "UPDATE agent_sessions SET ended_at=?, status='ended' WHERE id=?");
  stmt.bind(1, now_utc());
  stmt.bind(2, session_id);
  stmt.step_done();
}

void Storage::touch_file(const std::string &session_id, const std::string &filepath) {
  Statement stmt(db_, "INSERT INTO session_file_touches(session_id,filepath,touched_at) VALUES(?,?,?)");
  stmt.bind(1, session_id);
  stmt.bind(2, filepath);
  stmt.bind(3, now_utc());
  stmt.step_done();
}

int64_t Storage::add_decision(const std::string &session_id, const std::string &text) {
  Statement stmt(db_, "INSERT INTO decisions(session_id,text,created_at) VALUES(?,?,?)");
  stmt.bind(1, session_id);
  stmt.bind(2, text);
  stmt.bind(3, now_utc());
  stmt.step_done();
  return sqlite3_last_insert_rowid(db_);
}

std::vector<Decision> Storage::recent_decisions(int limit) {
  std::vector<Decision> out;
  Statement stmt(db_, "SELECT id,session_id,text,created_at FROM decisions ORDER BY id DESC LIMIT ?");
  stmt.bind(1, limit);
  while (stmt.step_row()) {
    out.push_back({stmt.column_int64(0), stmt.column_text(1), stmt.column_text(2), stmt.column_text(3)});
  }
  return out;
}

int64_t Storage::add_bus_message(const std::string &session_id, const std::string &channel, const std::string &message) {
  Statement stmt(db_, "INSERT INTO bus_messages(session_id,channel,message,created_at) VALUES(?,?,?,?)");
  stmt.bind(1, session_id);
  stmt.bind(2, channel);
  stmt.bind(3, message);
  stmt.bind(4, now_utc());
  stmt.step_done();
  return sqlite3_last_insert_rowid(db_);
}

std::string Storage::handoff_json() {
  nlohmann::json j;
  j["version"] = "0.1.0";
  j["generated_at_utc"] = now_utc();
  for (const auto &todo : list_todos("open", 25)) {
    j["active_todos"].push_back({{"id", todo.id}, {"filepath", todo.filepath}, {"line", todo.line}, {"tag", todo.tag}, {"text", todo.text}, {"priority", todo.priority}});
  }
  for (const auto &d : recent_decisions(15)) {
    j["recent_decisions"].push_back({{"id", d.id}, {"session_id", d.session_id}, {"text", d.text}, {"created_at", d.created_at}});
  }
  return j.dump();
}

std::string Storage::metrics_json() {
  nlohmann::json j;
  auto count = [&](const std::string &table) {
    Statement stmt(db_, "SELECT count(*) FROM " + table);
    return stmt.step_row() ? stmt.column_int64(0) : 0;
  };
  j["chunks"] = count("chunks");
  j["todos"] = count("todos");
  j["sessions"] = count("agent_sessions");
  j["decisions"] = count("decisions");
  j["bus_messages"] = count("bus_messages");
  return j.dump();
}

}  // namespace ragd
