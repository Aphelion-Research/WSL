#pragma once

// Minimal SQLite declarations used because this WSL image has libsqlite3 but
// not sqlite3.h. Linkage still uses the system SQLite shared library.

extern "C" {
struct sqlite3;
struct sqlite3_stmt;

using sqlite3_destructor_type = void (*)(void *);

int sqlite3_open(const char *filename, sqlite3 **ppDb);
int sqlite3_close(sqlite3 *);
int sqlite3_exec(sqlite3 *, const char *sql, int (*callback)(void *, int, char **, char **), void *, char **errmsg);
void sqlite3_free(void *);
const char *sqlite3_errmsg(sqlite3 *);
int sqlite3_prepare_v2(sqlite3 *, const char *zSql, int nByte, sqlite3_stmt **ppStmt, const char **pzTail);
int sqlite3_step(sqlite3_stmt *);
int sqlite3_finalize(sqlite3_stmt *);
int sqlite3_reset(sqlite3_stmt *);
int sqlite3_bind_text(sqlite3_stmt *, int, const char *, int, sqlite3_destructor_type);
int sqlite3_bind_int(sqlite3_stmt *, int, int);
int sqlite3_bind_int64(sqlite3_stmt *, int, long long);
int sqlite3_bind_double(sqlite3_stmt *, int, double);
int sqlite3_bind_null(sqlite3_stmt *, int);
int sqlite3_column_int(sqlite3_stmt *, int);
long long sqlite3_column_int64(sqlite3_stmt *, int);
double sqlite3_column_double(sqlite3_stmt *, int);
const unsigned char *sqlite3_column_text(sqlite3_stmt *, int);
int sqlite3_column_count(sqlite3_stmt *);
const char *sqlite3_column_name(sqlite3_stmt *, int);
long long sqlite3_last_insert_rowid(sqlite3 *);
}

constexpr int SQLITE_OK = 0;
constexpr int SQLITE_ROW = 100;
constexpr int SQLITE_DONE = 101;
#define RAGD_SQLITE_TRANSIENT ((sqlite3_destructor_type)-1)
