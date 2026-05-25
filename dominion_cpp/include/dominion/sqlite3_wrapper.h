// Stub wrapper for sqlite3 - will link against system libsqlite3.so.0
#pragma once

// SQLite3 type definitions (minimal subset)
typedef struct sqlite3 sqlite3;
typedef struct sqlite3_stmt sqlite3_stmt;

#define SQLITE_OK           0
#define SQLITE_ERROR        1
#define SQLITE_ROW          100
#define SQLITE_DONE         101
#define SQLITE_NULL         5

#define SQLITE_TRANSIENT ((void(*)(void *))(-1))

// Function declarations
extern "C" {
    int sqlite3_open(const char* filename, sqlite3** ppDb);
    int sqlite3_close(sqlite3* db);
    int sqlite3_exec(sqlite3* db, const char* sql, int (*callback)(void*,int,char**,char**), void* arg, char** errmsg);
    int sqlite3_prepare_v2(sqlite3* db, const char* sql, int nByte, sqlite3_stmt** ppStmt, const char** pzTail);
    int sqlite3_step(sqlite3_stmt* stmt);
    int sqlite3_finalize(sqlite3_stmt* stmt);
    int sqlite3_reset(sqlite3_stmt* stmt);
    int sqlite3_bind_text(sqlite3_stmt* stmt, int idx, const char* val, int n, void(*dest)(void*));
    int sqlite3_bind_int(sqlite3_stmt* stmt, int idx, int val);
    int sqlite3_bind_int64(sqlite3_stmt* stmt, int idx, long long val);
    int sqlite3_bind_double(sqlite3_stmt* stmt, int idx, double val);
    int sqlite3_bind_null(sqlite3_stmt* stmt, int idx);
    const unsigned char* sqlite3_column_text(sqlite3_stmt* stmt, int iCol);
    int sqlite3_column_int(sqlite3_stmt* stmt, int iCol);
    long long sqlite3_column_int64(sqlite3_stmt* stmt, int iCol);
    double sqlite3_column_double(sqlite3_stmt* stmt, int iCol);
    int sqlite3_column_type(sqlite3_stmt* stmt, int iCol);
    const char* sqlite3_errmsg(sqlite3* db);
    void sqlite3_free(void* ptr);
}
