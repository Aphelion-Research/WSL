#include "dominion_native/manifest_store.hpp"

#include "dominion_native/content_hash.hpp"
#include "ragd/sqlite_compat.h"

#include <chrono>
#include <filesystem>
#include <stdexcept>

namespace dominion_native {
namespace {

long long now_epoch() {
  return std::chrono::duration_cast<std::chrono::seconds>(std::chrono::system_clock::now().time_since_epoch()).count();
}

std::string text_or_empty(const unsigned char *text) {
  return text ? reinterpret_cast<const char *>(text) : "";
}

void throw_sqlite(sqlite3 *db, const std::string &context) {
  throw std::runtime_error(context + ": " + (db ? sqlite3_errmsg(db) : "no db"));
}

class Stmt {
 public:
  Stmt(sqlite3 *db, const std::string &sql) : db_(db) {
    if (sqlite3_prepare_v2(db_, sql.c_str(), -1, &stmt_, nullptr) != SQLITE_OK) throw_sqlite(db_, "prepare failed: " + sql);
  }
  ~Stmt() {
    if (stmt_) sqlite3_finalize(stmt_);
  }
  Stmt(const Stmt &) = delete;
  Stmt &operator=(const Stmt &) = delete;
  void bind(int index, const std::string &value) {
    if (sqlite3_bind_text(stmt_, index, value.c_str(), static_cast<int>(value.size()), RAGD_SQLITE_TRANSIENT) != SQLITE_OK) throw_sqlite(db_, "bind text failed");
  }
  void bind(int index, long long value) {
    if (sqlite3_bind_int64(stmt_, index, value) != SQLITE_OK) throw_sqlite(db_, "bind int64 failed");
  }
  bool step_row() {
    int rc = sqlite3_step(stmt_);
    if (rc == SQLITE_ROW) return true;
    if (rc == SQLITE_DONE) return false;
    throw_sqlite(db_, "step row failed");
    return false;
  }
  void step_done() {
    int rc = sqlite3_step(stmt_);
    if (rc != SQLITE_DONE) throw_sqlite(db_, "step done failed");
  }
  void reset() {
    if (sqlite3_reset(stmt_) != SQLITE_OK) throw_sqlite(db_, "reset failed");
  }
  long long int64(int index) const { return sqlite3_column_int64(stmt_, index); }
  std::string text(int index) const { return text_or_empty(sqlite3_column_text(stmt_, index)); }

 private:
  sqlite3 *db_ = nullptr;
  sqlite3_stmt *stmt_ = nullptr;
};

}  // namespace

ManifestStore::~ManifestStore() {
  if (db_) sqlite3_close(db_);
}

void ManifestStore::open(const std::filesystem::path &db_path) {
  if (db_path.has_parent_path()) std::filesystem::create_directories(db_path.parent_path());
  if (sqlite3_open(db_path.c_str(), &db_) != SQLITE_OK) throw_sqlite(db_, "open manifest db failed");
  exec("PRAGMA busy_timeout=5000;");
  exec("PRAGMA journal_mode=WAL;");
  exec("PRAGMA synchronous=NORMAL;");
}

void ManifestStore::exec(const std::string &sql) {
  char *err = nullptr;
  const int rc = sqlite3_exec(db_, sql.c_str(), nullptr, nullptr, &err);
  if (rc != SQLITE_OK) {
    std::string msg = err ? err : "unknown sqlite error";
    if (err) sqlite3_free(err);
    throw std::runtime_error("sqlite exec failed: " + msg + " sql=" + sql);
  }
}

void ManifestStore::initialize() {
  exec("BEGIN IMMEDIATE;");
  try {
    exec("CREATE TABLE IF NOT EXISTS native_migrations(version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at INTEGER NOT NULL);");
    Stmt migration(db_, "INSERT OR IGNORE INTO native_migrations(version,name,applied_at) VALUES(?,?,?)");
    migration.bind(1, 1LL);
    migration.bind(2, std::string("native_core_v1"));
    migration.bind(3, now_epoch());
    migration.step_done();
    exec("CREATE TABLE IF NOT EXISTS native_files(document_id TEXT PRIMARY KEY, repo_root TEXT NOT NULL, relative_path TEXT NOT NULL, absolute_path TEXT NOT NULL, language TEXT NOT NULL, kind TEXT NOT NULL, content_hash TEXT NOT NULL, size_bytes INTEGER NOT NULL, mtime_ns INTEGER NOT NULL, status TEXT NOT NULL, first_seen_at INTEGER NOT NULL, last_seen_at INTEGER NOT NULL, policy_fingerprint TEXT NOT NULL, metadata_json TEXT NOT NULL DEFAULT '{}');");
    exec("CREATE INDEX IF NOT EXISTS idx_native_files_repo_path ON native_files(repo_root, relative_path);");
    exec("CREATE INDEX IF NOT EXISTS idx_native_files_status ON native_files(status);");
    exec("CREATE TABLE IF NOT EXISTS native_scan_runs(scan_id TEXT PRIMARY KEY, repo_root TEXT NOT NULL, started_at INTEGER NOT NULL, ended_at INTEGER, status TEXT NOT NULL, files_seen INTEGER NOT NULL DEFAULT 0, files_included INTEGER NOT NULL DEFAULT 0, files_ignored INTEGER NOT NULL DEFAULT 0, errors_count INTEGER NOT NULL DEFAULT 0, plan_hash TEXT NOT NULL DEFAULT '', summary_json TEXT NOT NULL DEFAULT '{}');");
    exec("COMMIT;");
  } catch (...) {
    exec("ROLLBACK;");
    throw;
  }
}

std::string ManifestStore::commit_scan(const ScanPlan &plan) {
  initialize();
  const auto started = now_epoch();
  const auto scan_id = sha256_string(plan.root + ":" + std::to_string(started) + ":" + plan.plan_hash()).substr(0, 24);
  exec("BEGIN IMMEDIATE;");
  try {
    Stmt run(db_, "INSERT INTO native_scan_runs(scan_id,repo_root,started_at,status,files_seen,files_included,files_ignored,errors_count,plan_hash,summary_json) VALUES(?,?,?,?,?,?,?,?,?,?)");
    run.bind(1, scan_id);
    run.bind(2, plan.root);
    run.bind(3, started);
    run.bind(4, std::string("running"));
    run.bind(5, static_cast<long long>(plan.seen));
    run.bind(6, static_cast<long long>(plan.files.size()));
    run.bind(7, static_cast<long long>(plan.ignored.size()));
    run.bind(8, static_cast<long long>(plan.errors.size()));
    run.bind(9, plan.plan_hash());
    run.bind(10, plan.to_json(false, false).dump());
    run.step_done();

    Stmt upsert(db_, R"SQL(
      INSERT INTO native_files(document_id,repo_root,relative_path,absolute_path,language,kind,content_hash,size_bytes,mtime_ns,status,first_seen_at,last_seen_at,policy_fingerprint,metadata_json)
      VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
      ON CONFLICT(document_id) DO UPDATE SET
        repo_root=excluded.repo_root,
        relative_path=excluded.relative_path,
        absolute_path=excluded.absolute_path,
        language=excluded.language,
        kind=excluded.kind,
        content_hash=excluded.content_hash,
        size_bytes=excluded.size_bytes,
        mtime_ns=excluded.mtime_ns,
        status='active',
        last_seen_at=excluded.last_seen_at,
        policy_fingerprint=excluded.policy_fingerprint,
        metadata_json=excluded.metadata_json
    )SQL");
    for (const auto &file : plan.files) {
      const auto doc_id = document_id(plan.root, file.relative_path);
      upsert.bind(1, doc_id);
      upsert.bind(2, plan.root);
      upsert.bind(3, file.relative_path);
      upsert.bind(4, file.absolute_path);
      upsert.bind(5, file.language);
      upsert.bind(6, file.kind);
      upsert.bind(7, file.content_hash);
      upsert.bind(8, static_cast<long long>(file.size_bytes));
      upsert.bind(9, file.mtime_ns);
      upsert.bind(10, std::string("active"));
      upsert.bind(11, started);
      upsert.bind(12, started);
      upsert.bind(13, plan.policy_fingerprint);
      upsert.bind(14, std::string("{}"));
      upsert.step_done();
      upsert.reset();
    }
    Stmt del(db_, "UPDATE native_files SET status='deleted', last_seen_at=? WHERE repo_root=? AND status='active' AND last_seen_at<>?");
    del.bind(1, started);
    del.bind(2, plan.root);
    del.bind(3, started);
    del.step_done();
    Stmt finish(db_, "UPDATE native_scan_runs SET ended_at=?, status=? WHERE scan_id=?");
    finish.bind(1, now_epoch());
    finish.bind(2, plan.errors.empty() ? std::string("completed") : std::string("completed_with_errors"));
    finish.bind(3, scan_id);
    finish.step_done();
    exec("COMMIT;");
  } catch (...) {
    exec("ROLLBACK;");
    throw;
  }
  return scan_id;
}

nlohmann::json ManifestStore::doctor_json() {
  initialize();
  nlohmann::json j;
  j["ok"] = true;
  j["checks"] = nlohmann::json::array();
  long long duplicate_paths = 0;
  Stmt dup(db_, "SELECT COUNT(*) FROM (SELECT repo_root,relative_path,COUNT(*) AS n FROM native_files WHERE status='active' GROUP BY repo_root,relative_path HAVING n>1)");
  if (dup.step_row()) duplicate_paths = dup.int64(0);
  j["checks"].push_back({{"name", "duplicate_active_paths"}, {"status", duplicate_paths == 0 ? "pass" : "fail"}, {"count", duplicate_paths}});
  long long active = 0;
  Stmt active_stmt(db_, "SELECT COUNT(*) FROM native_files WHERE status='active'");
  if (active_stmt.step_row()) active = active_stmt.int64(0);
  j["active_files"] = active;
  if (duplicate_paths != 0) {
    j["ok"] = false;
    j["status"] = "fail";
  } else {
    j["status"] = "pass";
  }
  return j;
}

nlohmann::json manifest_init_json(const std::filesystem::path &db_path) {
  ManifestStore store;
  store.open(db_path);
  store.initialize();
  return {{"ok", true}, {"db", db_path.string()}, {"status", "initialized"}};
}

nlohmann::json manifest_scan_json(const std::filesystem::path &db_path, const std::filesystem::path &repo_root) {
  auto plan = build_scan_plan(repo_root);
  ManifestStore store;
  store.open(db_path);
  const auto scan_id = store.commit_scan(plan);
  auto payload = plan.to_json(false, false);
  payload["scan_id"] = scan_id;
  payload["db"] = db_path.string();
  return payload;
}

nlohmann::json manifest_doctor_json(const std::filesystem::path &db_path) {
  ManifestStore store;
  store.open(db_path);
  auto j = store.doctor_json();
  j["db"] = db_path.string();
  return j;
}

}  // namespace dominion_native
