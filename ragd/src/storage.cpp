#include "ragd/storage.h"

#include <algorithm>
#include <chrono>
#include <iomanip>
#include <nlohmann/json.hpp>
#include <random>
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

int64_t now_epoch() {
  return std::chrono::duration_cast<std::chrono::seconds>(std::chrono::system_clock::now().time_since_epoch()).count();
}

int64_t now_millis() {
  return std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::system_clock::now().time_since_epoch()).count();
}

bool table_has_column(sqlite3 *db, const std::string &table, const std::string &column) {
  Statement stmt(db, "PRAGMA table_info(" + table + ")");
  while (stmt.step_row()) {
    if (stmt.column_text(1) == column) return true;
  }
  return false;
}

void add_column_if_missing(Storage &storage, sqlite3 *db, const std::string &table, const std::string &column, const std::string &definition) {
  if (!table_has_column(db, table, column)) storage.exec("ALTER TABLE " + table + " ADD COLUMN " + definition);
}

std::string sanitize_fts_query(const std::string &query) {
  std::vector<std::string> tokens;
  std::string current;
  for (char ch : query) {
    if (std::isalnum(static_cast<unsigned char>(ch)) || ch == '_') {
      current.push_back(static_cast<char>(std::tolower(static_cast<unsigned char>(ch))));
    } else if (!current.empty()) {
      tokens.push_back(current);
      current.clear();
    }
  }
  if (!current.empty()) tokens.push_back(current);
  std::ostringstream out;
  for (std::size_t i = 0; i < tokens.size(); ++i) {
    if (i) out << " OR ";
    out << tokens[i];
  }
  return out.str();
}

std::string json_array_or_empty(const std::string &value) {
  auto parsed = nlohmann::json::parse(value.empty() ? "[]" : value, nullptr, false);
  return parsed.is_array() ? parsed.dump() : "[]";
}

Chunk read_chunk_row(Statement &stmt) {
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
  c.summary = stmt.column_text(11);
  c.repo_root = stmt.column_text(12);
  c.git_commit = stmt.column_text(13);
  c.indexed_at = stmt.column_int64(14);
  c.modified_at = stmt.column_int64(15);
  return c;
}

nlohmann::json todo_to_json(const Todo &todo) {
  return {
      {"id", todo.id},
      {"todo_id", todo.id},
      {"filepath", todo.filepath},
      {"line_number", todo.line},
      {"line", todo.line},
      {"kind", todo.tag},
      {"tag", todo.tag},
      {"content", todo.text},
      {"text", todo.text},
      {"symbol_name", todo.symbol_name},
      {"priority", todo.priority},
      {"status", todo.status},
      {"assigned_to", todo.assigned_to},
      {"tags", nlohmann::json::parse(json_array_or_empty(todo.tags_json))},
  };
}

nlohmann::json session_to_json(const Session &s) {
  return {
      {"session_id", s.id},
      {"id", s.id},
      {"agent_name", s.agent},
      {"agent", s.agent},
      {"started_at", s.started_at},
      {"ended_at", s.ended_at.empty() ? nlohmann::json(nullptr) : nlohmann::json(s.ended_at)},
      {"status", s.status},
      {"git_branch", s.git_branch},
      {"git_commit", s.git_commit},
      {"summary", s.summary},
      {"handoff_note", s.handoff_note},
      {"parent_session", s.parent_session.empty() ? nlohmann::json(nullptr) : nlohmann::json(s.parent_session)},
  };
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
    throw_sqlite(db_, "prepare failed: " + sql);
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

void Statement::bind_null(int index) {
  if (sqlite3_bind_null(stmt_, index) != SQLITE_OK) throw_sqlite(db_, "bind null failed");
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
    throw std::runtime_error("sqlite exec failed: " + msg + " sql=" + sql);
  }
}

void Storage::initialize() {
  exec("PRAGMA journal_mode=WAL;");
  exec("PRAGMA synchronous=NORMAL;");
  exec("CREATE TABLE IF NOT EXISTS kv_store(key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at INTEGER NOT NULL DEFAULT 0);");
  add_column_if_missing(*this, db_, "kv_store", "updated_at", "updated_at INTEGER NOT NULL DEFAULT 0");

  exec("CREATE TABLE IF NOT EXISTS chunks(id INTEGER PRIMARY KEY AUTOINCREMENT, filepath TEXT NOT NULL, content TEXT NOT NULL, lang TEXT, chunk_type TEXT, symbol_name TEXT, line_start INTEGER, line_end INTEGER, content_hash TEXT, metadata_json TEXT DEFAULT '{}', status TEXT DEFAULT 'active', updated_at TEXT DEFAULT CURRENT_TIMESTAMP, summary TEXT DEFAULT '', repo_root TEXT DEFAULT '', git_commit TEXT DEFAULT '', indexed_at INTEGER DEFAULT 0, modified_at INTEGER DEFAULT 0, embedding BLOB, embed_model TEXT DEFAULT 'tfidf', fts_rowid INTEGER);");
  add_column_if_missing(*this, db_, "chunks", "summary", "summary TEXT DEFAULT ''");
  add_column_if_missing(*this, db_, "chunks", "repo_root", "repo_root TEXT DEFAULT ''");
  add_column_if_missing(*this, db_, "chunks", "git_commit", "git_commit TEXT DEFAULT ''");
  add_column_if_missing(*this, db_, "chunks", "indexed_at", "indexed_at INTEGER DEFAULT 0");
  add_column_if_missing(*this, db_, "chunks", "modified_at", "modified_at INTEGER DEFAULT 0");
  add_column_if_missing(*this, db_, "chunks", "embedding", "embedding BLOB");
  add_column_if_missing(*this, db_, "chunks", "embed_model", "embed_model TEXT DEFAULT 'tfidf'");
  add_column_if_missing(*this, db_, "chunks", "fts_rowid", "fts_rowid INTEGER");
  exec("CREATE INDEX IF NOT EXISTS idx_chunks_identity ON chunks(filepath,line_start,line_end,content_hash);");
  exec("CREATE VIRTUAL TABLE IF NOT EXISTS fts_chunks USING fts5(content, filepath, chunk_id UNINDEXED);");

  exec("CREATE TABLE IF NOT EXISTS agent_sessions(id TEXT PRIMARY KEY, agent TEXT, started_at TEXT, ended_at TEXT, status TEXT, git_branch TEXT DEFAULT '', git_commit TEXT DEFAULT '', summary TEXT DEFAULT '', handoff_note TEXT DEFAULT '', parent_session TEXT DEFAULT '');");
  add_column_if_missing(*this, db_, "agent_sessions", "git_branch", "git_branch TEXT DEFAULT ''");
  add_column_if_missing(*this, db_, "agent_sessions", "git_commit", "git_commit TEXT DEFAULT ''");
  add_column_if_missing(*this, db_, "agent_sessions", "summary", "summary TEXT DEFAULT ''");
  add_column_if_missing(*this, db_, "agent_sessions", "handoff_note", "handoff_note TEXT DEFAULT ''");
  add_column_if_missing(*this, db_, "agent_sessions", "parent_session", "parent_session TEXT DEFAULT ''");

  exec("CREATE TABLE IF NOT EXISTS session_file_touches(id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, filepath TEXT, action TEXT DEFAULT 'analyze', touched_at TEXT, note TEXT DEFAULT '');");
  add_column_if_missing(*this, db_, "session_file_touches", "action", "action TEXT DEFAULT 'analyze'");
  add_column_if_missing(*this, db_, "session_file_touches", "note", "note TEXT DEFAULT ''");

  exec("CREATE TABLE IF NOT EXISTS decisions(id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, filepath TEXT DEFAULT '', text TEXT, rationale TEXT DEFAULT '', alternatives TEXT DEFAULT '[]', tags TEXT DEFAULT '[]', created_at TEXT);");
  add_column_if_missing(*this, db_, "decisions", "filepath", "filepath TEXT DEFAULT ''");
  add_column_if_missing(*this, db_, "decisions", "rationale", "rationale TEXT DEFAULT ''");
  add_column_if_missing(*this, db_, "decisions", "alternatives", "alternatives TEXT DEFAULT '[]'");
  add_column_if_missing(*this, db_, "decisions", "tags", "tags TEXT DEFAULT '[]'");

  exec("CREATE TABLE IF NOT EXISTS todos(id INTEGER PRIMARY KEY AUTOINCREMENT, filepath TEXT, line INTEGER, tag TEXT, text TEXT, symbol_name TEXT DEFAULT '', priority INTEGER, status TEXT DEFAULT 'open', assigned_to TEXT DEFAULT '', content_hash TEXT UNIQUE, tags TEXT DEFAULT '[]', created_at TEXT, updated_at TEXT, resolved_at TEXT, session_id TEXT DEFAULT '');");
  add_column_if_missing(*this, db_, "todos", "symbol_name", "symbol_name TEXT DEFAULT ''");
  add_column_if_missing(*this, db_, "todos", "assigned_to", "assigned_to TEXT DEFAULT ''");
  add_column_if_missing(*this, db_, "todos", "tags", "tags TEXT DEFAULT '[]'");
  add_column_if_missing(*this, db_, "todos", "resolved_at", "resolved_at TEXT");
  add_column_if_missing(*this, db_, "todos", "session_id", "session_id TEXT DEFAULT ''");

  exec("CREATE TABLE IF NOT EXISTS bus_messages(id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, kind TEXT DEFAULT 'broadcast', topic TEXT DEFAULT 'general', payload TEXT, sent_at INTEGER DEFAULT 0, ttl INTEGER DEFAULT 0, channel TEXT, message TEXT, created_at TEXT);");
  add_column_if_missing(*this, db_, "bus_messages", "kind", "kind TEXT DEFAULT 'broadcast'");
  add_column_if_missing(*this, db_, "bus_messages", "topic", "topic TEXT DEFAULT 'general'");
  add_column_if_missing(*this, db_, "bus_messages", "payload", "payload TEXT");
  add_column_if_missing(*this, db_, "bus_messages", "sent_at", "sent_at INTEGER DEFAULT 0");
  add_column_if_missing(*this, db_, "bus_messages", "ttl", "ttl INTEGER DEFAULT 0");

  exec("CREATE TABLE IF NOT EXISTS file_locks(filepath TEXT PRIMARY KEY, session_id TEXT, locked_at INTEGER, note TEXT DEFAULT '');");
  exec("CREATE TABLE IF NOT EXISTS dead_zones(id INTEGER PRIMARY KEY AUTOINCREMENT, filepath TEXT, kind TEXT DEFAULT '', symbol_name TEXT DEFAULT '', detail TEXT, confidence REAL DEFAULT 0.0, detected_at INTEGER DEFAULT 0, acknowledged INTEGER DEFAULT 0, reason TEXT, severity INTEGER, created_at TEXT);");
  add_column_if_missing(*this, db_, "dead_zones", "kind", "kind TEXT DEFAULT ''");
  add_column_if_missing(*this, db_, "dead_zones", "symbol_name", "symbol_name TEXT DEFAULT ''");
  add_column_if_missing(*this, db_, "dead_zones", "detail", "detail TEXT");
  add_column_if_missing(*this, db_, "dead_zones", "confidence", "confidence REAL DEFAULT 0.0");
  add_column_if_missing(*this, db_, "dead_zones", "detected_at", "detected_at INTEGER DEFAULT 0");
  add_column_if_missing(*this, db_, "dead_zones", "acknowledged", "acknowledged INTEGER DEFAULT 0");

  exec("CREATE TABLE IF NOT EXISTS chunk_history(id INTEGER PRIMARY KEY AUTOINCREMENT, chunk_id INTEGER, git_commit TEXT DEFAULT '', content TEXT DEFAULT '', event TEXT, indexed_at INTEGER DEFAULT 0, created_at TEXT);");
  add_column_if_missing(*this, db_, "chunk_history", "git_commit", "git_commit TEXT DEFAULT ''");
  add_column_if_missing(*this, db_, "chunk_history", "content", "content TEXT DEFAULT ''");
  add_column_if_missing(*this, db_, "chunk_history", "indexed_at", "indexed_at INTEGER DEFAULT 0");
  exec("CREATE TABLE IF NOT EXISTS symbol_edges(id INTEGER PRIMARY KEY AUTOINCREMENT, from_symbol TEXT, to_symbol TEXT, filepath TEXT, created_at INTEGER);");

  record_metric("schema_version", "2");
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
  int64_t id = 0;
  Statement existing(db_, "SELECT id FROM chunks WHERE filepath=? AND line_start=? AND line_end=? AND content_hash=? ORDER BY id DESC LIMIT 1");
  existing.bind(1, chunk.filepath);
  existing.bind(2, chunk.line_start);
  existing.bind(3, chunk.line_end);
  existing.bind(4, chunk.content_hash);
  if (existing.step_row()) id = existing.column_int64(0);

  if (id > 0) {
    Statement upd(db_, "UPDATE chunks SET content=?,lang=?,chunk_type=?,symbol_name=?,metadata_json=?,status=?,updated_at=?,summary=?,repo_root=?,git_commit=?,indexed_at=?,modified_at=?,embed_model=? WHERE id=?");
    upd.bind(1, chunk.content);
    upd.bind(2, chunk.lang);
    upd.bind(3, chunk.chunk_type);
    upd.bind(4, chunk.symbol_name);
    upd.bind(5, chunk.metadata_json.empty() ? "{}" : chunk.metadata_json);
    upd.bind(6, chunk.status.empty() ? "active" : chunk.status);
    upd.bind(7, now_utc());
    upd.bind(8, chunk.summary);
    upd.bind(9, chunk.repo_root);
    upd.bind(10, chunk.git_commit);
    upd.bind(11, chunk.indexed_at ? chunk.indexed_at : now_epoch());
    upd.bind(12, chunk.modified_at);
    upd.bind(13, "tfidf");
    upd.bind(14, id);
    upd.step_done();
  } else {
    Statement stmt(db_, "INSERT INTO chunks(filepath,content,lang,chunk_type,symbol_name,line_start,line_end,content_hash,metadata_json,status,updated_at,summary,repo_root,git_commit,indexed_at,modified_at,embed_model) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)");
    stmt.bind(1, chunk.filepath);
    stmt.bind(2, chunk.content);
    stmt.bind(3, chunk.lang);
    stmt.bind(4, chunk.chunk_type);
    stmt.bind(5, chunk.symbol_name);
    stmt.bind(6, chunk.line_start);
    stmt.bind(7, chunk.line_end);
    stmt.bind(8, chunk.content_hash);
    stmt.bind(9, chunk.metadata_json.empty() ? "{}" : chunk.metadata_json);
    stmt.bind(10, chunk.status.empty() ? "active" : chunk.status);
    stmt.bind(11, now_utc());
    stmt.bind(12, chunk.summary);
    stmt.bind(13, chunk.repo_root);
    stmt.bind(14, chunk.git_commit);
    stmt.bind(15, chunk.indexed_at ? chunk.indexed_at : now_epoch());
    stmt.bind(16, chunk.modified_at);
    stmt.bind(17, "tfidf");
    stmt.step_done();
    id = sqlite3_last_insert_rowid(db_);

    Statement hist(db_, "INSERT INTO chunk_history(chunk_id,git_commit,content,event,indexed_at,created_at) VALUES(?,?,?,?,?,?)");
    hist.bind(1, id);
    hist.bind(2, chunk.git_commit);
    hist.bind(3, chunk.content);
    hist.bind(4, "index");
    hist.bind(5, now_epoch());
    hist.bind(6, now_utc());
    hist.step_done();
  }

  Statement clear_fts(db_, "DELETE FROM fts_chunks WHERE chunk_id=?");
  clear_fts.bind(1, id);
  clear_fts.step_done();

  Statement fts(db_, "INSERT INTO fts_chunks(content, filepath, chunk_id) VALUES(?,?,?)");
  fts.bind(1, chunk.content);
  fts.bind(2, chunk.filepath);
  fts.bind(3, id);
  fts.step_done();
  return id;
}

std::vector<QueryResult> Storage::search_fts(const std::string &query, int limit) {
  std::vector<QueryResult> out;
  auto fts_query = sanitize_fts_query(query);
  if (fts_query.empty()) return out;
  Statement stmt(db_, "SELECT c.id,c.filepath,c.content,-bm25(fts_chunks),c.lang,c.chunk_type,c.symbol_name,c.line_start,c.line_end,c.summary,c.git_commit,c.content_hash,c.repo_root,c.status,c.indexed_at,c.modified_at FROM fts_chunks JOIN chunks c ON c.id=fts_chunks.chunk_id WHERE fts_chunks MATCH ? AND c.status='active' ORDER BY bm25(fts_chunks) LIMIT ?");
  stmt.bind(1, fts_query);
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
    r.summary = stmt.column_text(9);
    r.git_commit = stmt.column_text(10);
    r.content_hash = stmt.column_text(11);
    r.repo_root = stmt.column_text(12);
    r.status = stmt.column_text(13);
    r.indexed_at = stmt.column_int64(14);
    r.modified_at = stmt.column_int64(15);
    out.push_back(std::move(r));
  }
  return out;
}

std::vector<QueryResult> Storage::search_like(const std::string &query, int limit) {
  std::vector<QueryResult> out;
  Statement stmt(db_, "SELECT id,filepath,content,lang,chunk_type,symbol_name,line_start,line_end,summary,git_commit,content_hash,repo_root,status,indexed_at,modified_at FROM chunks WHERE status='active' AND (content LIKE ? OR filepath LIKE ? OR symbol_name LIKE ?) ORDER BY id DESC LIMIT ?");
  std::string needle = "%" + query + "%";
  stmt.bind(1, needle);
  stmt.bind(2, needle);
  stmt.bind(3, needle);
  stmt.bind(4, limit);
  while (stmt.step_row()) {
    QueryResult r;
    r.chunk_id = stmt.column_int64(0);
    r.filepath = stmt.column_text(1);
    r.content = stmt.column_text(2);
    r.lang = stmt.column_text(3);
    r.chunk_type = stmt.column_text(4);
    r.symbol_name = stmt.column_text(5);
    r.line_start = stmt.column_int(6);
    r.line_end = stmt.column_int(7);
    r.summary = stmt.column_text(8);
    r.git_commit = stmt.column_text(9);
    r.content_hash = stmt.column_text(10);
    r.repo_root = stmt.column_text(11);
    r.status = stmt.column_text(12);
    r.indexed_at = stmt.column_int64(13);
    r.modified_at = stmt.column_int64(14);
    r.score = 1.0;
    out.push_back(std::move(r));
  }
  return out;
}

std::vector<Chunk> Storage::recent_chunks(int limit) {
  std::vector<Chunk> out;
  Statement stmt(db_, "SELECT id,filepath,content,lang,chunk_type,symbol_name,line_start,line_end,content_hash,metadata_json,status,summary,repo_root,git_commit,indexed_at,modified_at FROM chunks WHERE status='active' ORDER BY id DESC LIMIT ?");
  stmt.bind(1, limit);
  while (stmt.step_row()) out.push_back(read_chunk_row(stmt));
  return out;
}

Chunk Storage::get_chunk(int64_t id) {
  Statement stmt(db_, "SELECT id,filepath,content,lang,chunk_type,symbol_name,line_start,line_end,content_hash,metadata_json,status,summary,repo_root,git_commit,indexed_at,modified_at FROM chunks WHERE id=?");
  stmt.bind(1, id);
  if (stmt.step_row()) return read_chunk_row(stmt);
  return {};
}

int Storage::mark_file_deleted(const std::string &filepath) {
  Statement stmt(db_, "UPDATE chunks SET status='deleted', updated_at=? WHERE filepath=? AND status='active'");
  stmt.bind(1, now_utc());
  stmt.bind(2, filepath);
  stmt.step_done();
  return sqlite3_changes(db_);
}

int Storage::active_chunks_for_file(const std::string &filepath) {
  Statement stmt(db_, "SELECT COUNT(*) FROM chunks WHERE filepath=? AND status='active'");
  stmt.bind(1, filepath);
  return stmt.step_row() ? stmt.column_int(0) : 0;
}

int64_t Storage::add_todo(const Todo &todo) {
  auto ts = now_utc();
  Statement stmt(db_, "INSERT OR IGNORE INTO todos(filepath,line,tag,text,symbol_name,priority,status,assigned_to,content_hash,tags,created_at,updated_at,session_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)");
  stmt.bind(1, todo.filepath);
  stmt.bind(2, todo.line);
  stmt.bind(3, todo.tag.empty() ? "TODO" : todo.tag);
  stmt.bind(4, todo.text);
  stmt.bind(5, todo.symbol_name);
  stmt.bind(6, todo.priority);
  stmt.bind(7, todo.status.empty() ? "open" : todo.status);
  stmt.bind(8, todo.assigned_to);
  stmt.bind(9, todo.content_hash.empty() ? sha256ish(todo.filepath + todo.text) : todo.content_hash);
  stmt.bind(10, json_array_or_empty(todo.tags_json));
  stmt.bind(11, ts);
  stmt.bind(12, ts);
  stmt.bind(13, "");
  stmt.step_done();

  Statement upd(db_, "UPDATE todos SET updated_at=?, status=CASE WHEN status='done' THEN 'open' ELSE status END WHERE content_hash=?");
  upd.bind(1, ts);
  upd.bind(2, todo.content_hash.empty() ? sha256ish(todo.filepath + todo.text) : todo.content_hash);
  upd.step_done();

  Statement sel(db_, "SELECT id FROM todos WHERE content_hash=?");
  sel.bind(1, todo.content_hash.empty() ? sha256ish(todo.filepath + todo.text) : todo.content_hash);
  return sel.step_row() ? sel.column_int64(0) : sqlite3_last_insert_rowid(db_);
}

std::vector<Todo> Storage::list_todos(const std::string &status, int limit) {
  return list_todos_filtered(status, 99, "", limit);
}

std::vector<Todo> Storage::list_todos_filtered(const std::string &status, int priority_max, const std::string &kind, int limit) {
  std::vector<Todo> out;
  std::string sql = "SELECT id,filepath,line,tag,text,priority,status,content_hash,symbol_name,assigned_to,tags FROM todos WHERE 1=1";
  if (!status.empty()) sql += " AND status=?";
  if (priority_max > 0 && priority_max < 99) sql += " AND priority<=?";
  if (!kind.empty()) sql += " AND tag=?";
  sql += " ORDER BY priority ASC,id DESC LIMIT ?";
  Statement stmt(db_, sql);
  int bind = 1;
  if (!status.empty()) stmt.bind(bind++, status);
  if (priority_max > 0 && priority_max < 99) stmt.bind(bind++, priority_max);
  if (!kind.empty()) stmt.bind(bind++, kind);
  stmt.bind(bind, limit);
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
    t.symbol_name = stmt.column_text(8);
    t.assigned_to = stmt.column_text(9);
    t.tags_json = stmt.column_text(10);
    out.push_back(std::move(t));
  }
  return out;
}

void Storage::update_todo_status(int64_t id, const std::string &status) {
  Statement stmt(db_, "UPDATE todos SET status=?, updated_at=?, resolved_at=CASE WHEN ? IN ('done','resolved') THEN ? ELSE resolved_at END WHERE id=?");
  stmt.bind(1, status);
  stmt.bind(2, now_utc());
  stmt.bind(3, status);
  stmt.bind(4, now_utc());
  stmt.bind(5, id);
  stmt.step_done();
}

void Storage::update_todo(int64_t id, const std::string &status, const std::string &assigned_to, int priority) {
  Statement stmt(db_, "UPDATE todos SET status=COALESCE(NULLIF(?,''),status), assigned_to=COALESCE(NULLIF(?,''),assigned_to), priority=CASE WHEN ?>0 THEN ? ELSE priority END, updated_at=? WHERE id=?");
  stmt.bind(1, status);
  stmt.bind(2, assigned_to);
  stmt.bind(3, priority);
  stmt.bind(4, priority);
  stmt.bind(5, now_utc());
  stmt.bind(6, id);
  stmt.step_done();
}

std::string Storage::start_session(const std::string &agent, const std::string &git_branch, const std::string &parent_session) {
  std::string seed = agent + now_utc() + std::to_string(now_millis()) + std::to_string(std::random_device{}());
  std::string id = "sess_" + sha256ish(seed).substr(0, 16);
  Statement stmt(db_, "INSERT INTO agent_sessions(id,agent,started_at,status,git_branch,parent_session) VALUES(?,?,?,?,?,?)");
  stmt.bind(1, id);
  stmt.bind(2, agent.empty() ? "unknown-agent" : agent);
  stmt.bind(3, now_utc());
  stmt.bind(4, "active");
  stmt.bind(5, git_branch);
  stmt.bind(6, parent_session);
  stmt.step_done();
  return id;
}

void Storage::end_session(const std::string &session_id, const std::string &summary, const std::string &handoff_note, const std::string &status) {
  Statement stmt(db_, "UPDATE agent_sessions SET ended_at=?, status=?, summary=COALESCE(NULLIF(?,''),summary), handoff_note=COALESCE(NULLIF(?,''),handoff_note) WHERE id=?");
  stmt.bind(1, now_utc());
  stmt.bind(2, status.empty() ? "completed" : status);
  stmt.bind(3, summary);
  stmt.bind(4, handoff_note);
  stmt.bind(5, session_id);
  stmt.step_done();
}

void Storage::touch_file(const std::string &session_id, const std::string &filepath, const std::string &action, const std::string &note) {
  Statement stmt(db_, "INSERT INTO session_file_touches(session_id,filepath,action,touched_at,note) VALUES(?,?,?,?,?)");
  stmt.bind(1, session_id);
  stmt.bind(2, filepath);
  stmt.bind(3, action.empty() ? "analyze" : action);
  stmt.bind(4, now_utc());
  stmt.bind(5, note);
  stmt.step_done();
}

int64_t Storage::add_decision(const std::string &session_id, const std::string &text, const std::string &filepath, const std::string &rationale, const std::string &alternatives_json, const std::string &tags_json) {
  Statement stmt(db_, "INSERT INTO decisions(session_id,filepath,text,rationale,alternatives,tags,created_at) VALUES(?,?,?,?,?,?,?)");
  stmt.bind(1, session_id);
  stmt.bind(2, filepath);
  stmt.bind(3, text);
  stmt.bind(4, rationale);
  stmt.bind(5, json_array_or_empty(alternatives_json));
  stmt.bind(6, json_array_or_empty(tags_json));
  stmt.bind(7, now_utc());
  stmt.step_done();
  return sqlite3_last_insert_rowid(db_);
}

std::vector<Decision> Storage::recent_decisions(int limit) {
  std::vector<Decision> out;
  Statement stmt(db_, "SELECT id,session_id,filepath,text,rationale,alternatives,tags,created_at FROM decisions ORDER BY id DESC LIMIT ?");
  stmt.bind(1, limit);
  while (stmt.step_row()) {
    Decision d;
    d.id = stmt.column_int64(0);
    d.session_id = stmt.column_text(1);
    d.filepath = stmt.column_text(2);
    d.text = stmt.column_text(3);
    d.rationale = stmt.column_text(4);
    d.alternatives_json = stmt.column_text(5);
    d.tags_json = stmt.column_text(6);
    d.created_at = stmt.column_text(7);
    out.push_back(std::move(d));
  }
  return out;
}

std::vector<Session> Storage::list_sessions(const std::string &status, int limit) {
  std::vector<Session> out;
  std::string sql = "SELECT id,agent,started_at,ended_at,status,git_branch,git_commit,summary,handoff_note,parent_session FROM agent_sessions";
  if (!status.empty()) sql += " WHERE status=?";
  sql += " ORDER BY started_at DESC LIMIT ?";
  Statement stmt(db_, sql);
  if (!status.empty()) {
    stmt.bind(1, status);
    stmt.bind(2, limit);
  } else {
    stmt.bind(1, limit);
  }
  while (stmt.step_row()) {
    Session s;
    s.id = stmt.column_text(0);
    s.agent = stmt.column_text(1);
    s.started_at = stmt.column_text(2);
    s.ended_at = stmt.column_text(3);
    s.status = stmt.column_text(4);
    s.git_branch = stmt.column_text(5);
    s.git_commit = stmt.column_text(6);
    s.summary = stmt.column_text(7);
    s.handoff_note = stmt.column_text(8);
    s.parent_session = stmt.column_text(9);
    out.push_back(std::move(s));
  }
  return out;
}

std::string Storage::session_json(const std::string &session_id) {
  Statement stmt(db_, "SELECT id,agent,started_at,ended_at,status,git_branch,git_commit,summary,handoff_note,parent_session FROM agent_sessions WHERE id=?");
  stmt.bind(1, session_id);
  nlohmann::json j;
  if (stmt.step_row()) {
    Session s;
    s.id = stmt.column_text(0);
    s.agent = stmt.column_text(1);
    s.started_at = stmt.column_text(2);
    s.ended_at = stmt.column_text(3);
    s.status = stmt.column_text(4);
    s.git_branch = stmt.column_text(5);
    s.git_commit = stmt.column_text(6);
    s.summary = stmt.column_text(7);
    s.handoff_note = stmt.column_text(8);
    s.parent_session = stmt.column_text(9);
    j = session_to_json(s);
  }
  j["file_touches"] = nlohmann::json::array();
  Statement touches(db_, "SELECT filepath,action,touched_at,note FROM session_file_touches WHERE session_id=? ORDER BY id");
  touches.bind(1, session_id);
  while (touches.step_row()) {
    j["file_touches"].push_back({{"filepath", touches.column_text(0)}, {"action", touches.column_text(1)}, {"touched_at", touches.column_text(2)}, {"note", touches.column_text(3)}});
  }
  j["decisions"] = nlohmann::json::array();
  Statement decisions(db_, "SELECT id,filepath,text,rationale,tags,created_at FROM decisions WHERE session_id=? ORDER BY id");
  decisions.bind(1, session_id);
  while (decisions.step_row()) {
    j["decisions"].push_back({{"id", decisions.column_int64(0)}, {"filepath", decisions.column_text(1)}, {"decision", decisions.column_text(2)}, {"rationale", decisions.column_text(3)}, {"tags", nlohmann::json::parse(json_array_or_empty(decisions.column_text(4)))}, {"created_at", decisions.column_text(5)}});
  }
  return j.dump();
}

std::string Storage::file_history_json(const std::string &filepath) {
  nlohmann::json j;
  j["filepath"] = filepath;
  j["sessions"] = nlohmann::json::array();
  Statement stmt(db_, "SELECT s.id,s.agent,s.started_at,s.ended_at,s.status,t.action,t.touched_at,t.note FROM session_file_touches t LEFT JOIN agent_sessions s ON s.id=t.session_id WHERE t.filepath=? ORDER BY t.id DESC LIMIT 100");
  stmt.bind(1, filepath);
  while (stmt.step_row()) {
    j["sessions"].push_back({{"session_id", stmt.column_text(0)}, {"agent_name", stmt.column_text(1)}, {"started_at", stmt.column_text(2)}, {"ended_at", stmt.column_text(3)}, {"status", stmt.column_text(4)}, {"action", stmt.column_text(5)}, {"touched_at", stmt.column_text(6)}, {"note", stmt.column_text(7)}});
  }
  return j.dump();
}

std::string Storage::agent_timeline_json(int limit) {
  nlohmann::json j;
  j["events"] = nlohmann::json::array();
  for (const auto &s : list_sessions("", limit)) j["events"].push_back(session_to_json(s));
  return j.dump();
}

int64_t Storage::add_bus_message(const std::string &session_id, const std::string &kind, const std::string &topic, const std::string &payload, int ttl) {
  Statement stmt(db_, "INSERT INTO bus_messages(session_id,kind,topic,payload,sent_at,ttl,channel,message,created_at) VALUES(?,?,?,?,?,?,?,?,?)");
  stmt.bind(1, session_id);
  stmt.bind(2, kind.empty() ? "broadcast" : kind);
  stmt.bind(3, topic.empty() ? "general" : topic);
  stmt.bind(4, payload);
  stmt.bind(5, now_epoch());
  stmt.bind(6, ttl);
  stmt.bind(7, topic.empty() ? "general" : topic);
  stmt.bind(8, payload);
  stmt.bind(9, now_utc());
  stmt.step_done();
  int64_t id = sqlite3_last_insert_rowid(db_);
  if (kind == "lock" || kind == "unlock") upsert_file_lock(topic, session_id, kind);
  return id;
}

std::string Storage::bus_messages_json(const std::string &topic, int64_t since_epoch) {
  nlohmann::json j;
  j["messages"] = nlohmann::json::array();
  std::string sql = "SELECT id,session_id,kind,topic,payload,sent_at,ttl FROM bus_messages WHERE (ttl=0 OR sent_at+ttl>=?)";
  if (!topic.empty()) sql += " AND topic=?";
  if (since_epoch > 0) sql += " AND sent_at>=?";
  sql += " ORDER BY id DESC LIMIT 200";
  Statement stmt(db_, sql);
  int bind = 1;
  stmt.bind(bind++, now_epoch());
  if (!topic.empty()) stmt.bind(bind++, topic);
  if (since_epoch > 0) stmt.bind(bind++, since_epoch);
  while (stmt.step_row()) {
    auto payload = nlohmann::json::parse(stmt.column_text(4).empty() ? "{}" : stmt.column_text(4), nullptr, false);
    j["messages"].push_back({{"id", stmt.column_int64(0)}, {"session_id", stmt.column_text(1)}, {"kind", stmt.column_text(2)}, {"topic", stmt.column_text(3)}, {"payload", payload.is_discarded() ? nlohmann::json(stmt.column_text(4)) : payload}, {"sent_at", stmt.column_int64(5)}, {"ttl", stmt.column_int(6)}});
  }
  return j.dump();
}

std::string Storage::bus_locks_json() {
  nlohmann::json j;
  j["locks"] = nlohmann::json::array();
  Statement stmt(db_, "SELECT filepath,session_id,locked_at,note FROM file_locks ORDER BY locked_at DESC");
  while (stmt.step_row()) {
    j["locks"].push_back({{"filepath", stmt.column_text(0)}, {"session_id", stmt.column_text(1)}, {"locked_at", stmt.column_int64(2)}, {"note", stmt.column_text(3)}});
  }
  return j.dump();
}

void Storage::upsert_file_lock(const std::string &filepath, const std::string &session_id, const std::string &action) {
  if (filepath.empty()) return;
  if (action == "unlock") {
    Statement stmt(db_, "DELETE FROM file_locks WHERE filepath=? AND (session_id=? OR ?='')");
    stmt.bind(1, filepath);
    stmt.bind(2, session_id);
    stmt.bind(3, session_id);
    stmt.step_done();
    return;
  }
  Statement stmt(db_, "INSERT OR REPLACE INTO file_locks(filepath,session_id,locked_at,note) VALUES(?,?,?,?)");
  stmt.bind(1, filepath);
  stmt.bind(2, session_id);
  stmt.bind(3, now_epoch());
  stmt.bind(4, "advisory lock");
  stmt.step_done();
}

int64_t Storage::add_dead_zone(const std::string &filepath, const std::string &kind, const std::string &symbol, const std::string &detail, double confidence) {
  Statement stmt(db_, "INSERT INTO dead_zones(filepath,kind,symbol_name,detail,confidence,detected_at,acknowledged,reason,severity,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)");
  stmt.bind(1, filepath);
  stmt.bind(2, kind);
  stmt.bind(3, symbol);
  stmt.bind(4, detail);
  stmt.bind(5, confidence);
  stmt.bind(6, now_epoch());
  stmt.bind(7, 0);
  stmt.bind(8, detail);
  stmt.bind(9, confidence > 0.8 ? 1 : 3);
  stmt.bind(10, now_utc());
  stmt.step_done();
  return sqlite3_last_insert_rowid(db_);
}

std::string Storage::dead_zones_json(bool acknowledged) {
  nlohmann::json j;
  j["dead_zones"] = nlohmann::json::array();
  Statement stmt(db_, "SELECT id,filepath,kind,symbol_name,detail,confidence,detected_at,acknowledged FROM dead_zones WHERE acknowledged=? ORDER BY confidence DESC,id DESC LIMIT 200");
  stmt.bind(1, acknowledged ? 1 : 0);
  while (stmt.step_row()) {
    j["dead_zones"].push_back({{"id", stmt.column_int64(0)}, {"filepath", stmt.column_text(1)}, {"kind", stmt.column_text(2)}, {"symbol_name", stmt.column_text(3)}, {"detail", stmt.column_text(4)}, {"confidence", stmt.column_double(5)}, {"detected_at", stmt.column_int64(6)}, {"acknowledged", stmt.column_int(7) != 0}});
  }
  return j.dump();
}

std::string Storage::symbols_json(const std::string &root, int depth) {
  nlohmann::json j;
  j["root"] = root;
  j["depth"] = depth;
  j["symbols"] = nlohmann::json::array();
  Statement stmt(db_, "SELECT symbol_name,filepath,chunk_type,line_start,line_end FROM chunks WHERE status='active' AND symbol_name<>'' ORDER BY filepath,line_start LIMIT 500");
  while (stmt.step_row()) {
    std::string symbol = stmt.column_text(0);
    if (!root.empty() && symbol.find(root) == std::string::npos) continue;
    j["symbols"].push_back({{"symbol_name", symbol}, {"filepath", stmt.column_text(1)}, {"chunk_type", stmt.column_text(2)}, {"line_start", stmt.column_int(3)}, {"line_end", stmt.column_int(4)}});
  }
  return j.dump();
}

void Storage::record_metric(const std::string &key, const std::string &value) {
  Statement stmt(db_, "INSERT OR REPLACE INTO kv_store(key,value,updated_at) VALUES(?,?,?)");
  stmt.bind(1, key);
  stmt.bind(2, value);
  stmt.bind(3, now_epoch());
  stmt.step_done();
}

std::string Storage::handoff_json() {
  nlohmann::json j;
  j["ragd_version"] = "1.0.0";
  j["version"] = "1.0.0";
  j["generated_at_utc"] = now_utc();
  j["embed_backend"] = "tfidf";
  j["active_todos"] = nlohmann::json::array();
  for (const auto &todo : list_todos_filtered("open", 99, "", 20)) j["active_todos"].push_back(todo_to_json(todo));
  j["recent_decisions"] = nlohmann::json::array();
  for (const auto &d : recent_decisions(10)) {
    j["recent_decisions"].push_back({{"id", d.id}, {"session_id", d.session_id}, {"filepath", d.filepath}, {"decision", d.text}, {"text", d.text}, {"rationale", d.rationale}, {"alternatives", nlohmann::json::parse(json_array_or_empty(d.alternatives_json))}, {"tags", nlohmann::json::parse(json_array_or_empty(d.tags_json))}, {"created_at", d.created_at}});
  }
  j["last_sessions"] = nlohmann::json::array();
  for (const auto &s : list_sessions("completed", 3)) j["last_sessions"].push_back(session_to_json(s));
  j["active_sessions"] = nlohmann::json::array();
  for (const auto &s : list_sessions("active", 20)) j["active_sessions"].push_back(session_to_json(s));
  j["dead_zones"] = nlohmann::json::parse(dead_zones_json(false))["dead_zones"];
  j["active_warnings"] = nlohmann::json::array();
  auto messages = nlohmann::json::parse(bus_messages_json());
  for (const auto &m : messages["messages"]) {
    if (m.value("kind", "") == "warning") j["active_warnings"].push_back(m);
  }
  j["indexed_paths"] = nlohmann::json::array();
  Statement paths(db_, "SELECT filepath,count(*) FROM chunks WHERE status='active' GROUP BY filepath ORDER BY filepath LIMIT 200");
  while (paths.step_row()) j["indexed_paths"].push_back({{"filepath", paths.column_text(0)}, {"chunks", paths.column_int64(1)}});
  return j.dump();
}

std::string Storage::metrics_json() {
  nlohmann::json j;
  auto count = [&](const std::string &table) {
    Statement stmt(db_, "SELECT count(*) FROM " + table);
    return stmt.step_row() ? stmt.column_int64(0) : 0;
  };
  j["status"] = "ok";
  j["chunks"] = count("chunks");
  j["active_chunks"] = [&] {
    Statement stmt(db_, "SELECT count(*) FROM chunks WHERE status='active'");
    return stmt.step_row() ? stmt.column_int64(0) : 0;
  }();
  j["todos"] = count("todos");
  j["sessions"] = count("agent_sessions");
  j["decisions"] = count("decisions");
  j["bus_messages"] = count("bus_messages");
  j["dead_zones"] = count("dead_zones");
  j["embed_backend"] = "tfidf";
  j["ragd_version"] = "1.0.0";
  j["retrieval_latency_ms"] = {{"p50", 0}, {"p95", 0}, {"p99", 0}};
  return j.dump();
}

}  // namespace ragd
