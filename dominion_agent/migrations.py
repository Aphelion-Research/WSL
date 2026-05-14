"""Schema migrations for Dominion Agent OS.

All migrations are additive. No destructive operations.
Migration table is always created first.
"""
from __future__ import annotations

import sqlite3
import time

# ---------------------------------------------------------------------------
# Schema SQL
# ---------------------------------------------------------------------------

_MIGRATION_1_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS agent_os_migrations(
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_sessions_v2(
    session_id TEXT PRIMARY KEY,
    agent_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'unknown',
    status TEXT NOT NULL DEFAULT 'active',
    started_at INTEGER NOT NULL,
    ended_at INTEGER,
    last_heartbeat INTEGER,
    git_branch TEXT DEFAULT '',
    git_commit_start TEXT DEFAULT '',
    git_commit_end TEXT DEFAULT '',
    parent_session_id TEXT DEFAULT '',
    metadata_json TEXT DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_sessions_status
    ON agent_sessions_v2(status);

CREATE TABLE IF NOT EXISTS agent_tasks(
    task_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    kind TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 5,
    status TEXT NOT NULL DEFAULT 'open',
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    claimed_by_session TEXT DEFAULT '',
    parent_task_id TEXT DEFAULT '',
    scope_json TEXT DEFAULT '{}',
    validation_json TEXT DEFAULT '{}',
    acceptance_json TEXT DEFAULT '{}',
    risk_json TEXT DEFAULT '{}',
    tags_json TEXT DEFAULT '[]',
    evidence_json TEXT DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_tasks_status
    ON agent_tasks(status);

CREATE TABLE IF NOT EXISTS agent_claims(
    claim_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    claimed_at INTEGER NOT NULL,
    released_at INTEGER,
    note TEXT DEFAULT '',
    UNIQUE(task_id, session_id, status)
);

CREATE INDEX IF NOT EXISTS idx_claims_task
    ON agent_claims(task_id);

CREATE TABLE IF NOT EXISTS agent_file_locks(
    lock_id TEXT PRIMARY KEY,
    filepath TEXT NOT NULL,
    session_id TEXT NOT NULL,
    task_id TEXT DEFAULT '',
    mode TEXT NOT NULL DEFAULT 'write',
    status TEXT NOT NULL DEFAULT 'active',
    locked_at INTEGER NOT NULL,
    released_at INTEGER,
    expires_at INTEGER,
    note TEXT DEFAULT '',
    UNIQUE(filepath, status)
);

CREATE INDEX IF NOT EXISTS idx_locks_filepath
    ON agent_file_locks(filepath, status);

CREATE TABLE IF NOT EXISTS agent_file_touches(
    touch_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    task_id TEXT DEFAULT '',
    filepath TEXT NOT NULL,
    action TEXT NOT NULL,
    touched_at INTEGER NOT NULL,
    git_commit TEXT DEFAULT '',
    note TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_touches_filepath
    ON agent_file_touches(filepath);

CREATE TABLE IF NOT EXISTS agent_reviews(
    review_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    reviewer_session_id TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    created_at INTEGER NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    findings_json TEXT DEFAULT '[]',
    commands_json TEXT DEFAULT '[]',
    verdict TEXT DEFAULT 'unknown'
);

CREATE INDEX IF NOT EXISTS idx_reviews_task
    ON agent_reviews(task_id);

CREATE TABLE IF NOT EXISTS agent_prompt_compilations(
    compilation_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    target_agent TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    prompt_hash TEXT NOT NULL,
    context_summary TEXT DEFAULT '',
    included_files_json TEXT DEFAULT '[]',
    validation_json TEXT DEFAULT '{}',
    output_path TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_compilations_task
    ON agent_prompt_compilations(task_id);

CREATE TABLE IF NOT EXISTS agent_complexity_snapshots(
    snapshot_id TEXT PRIMARY KEY,
    created_at INTEGER NOT NULL,
    package TEXT NOT NULL,
    score REAL NOT NULL,
    metrics_json TEXT NOT NULL,
    warnings_json TEXT DEFAULT '[]'
);

CREATE INDEX IF NOT EXISTS idx_complexity_package
    ON agent_complexity_snapshots(package, created_at);

CREATE TABLE IF NOT EXISTS agent_os_events(
    event_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at INTEGER NOT NULL,
    ragd_synced INTEGER NOT NULL DEFAULT 0,
    ragd_synced_at INTEGER
);

CREATE INDEX IF NOT EXISTS idx_events_synced
    ON agent_os_events(ragd_synced, created_at);
"""

# ---------------------------------------------------------------------------
# Migration registry
# ---------------------------------------------------------------------------

# Migration 2: fix agent_file_locks UNIQUE constraint.
# UNIQUE(filepath, status) wrongly blocks multiple read locks on the same file.
# Replaced with UNIQUE(filepath, session_id) which prevents double-locking by same session.
_MIGRATION_2_SQL = """
CREATE TABLE IF NOT EXISTS agent_file_locks_v2(
    lock_id TEXT PRIMARY KEY,
    filepath TEXT NOT NULL,
    session_id TEXT NOT NULL,
    task_id TEXT DEFAULT '',
    mode TEXT NOT NULL DEFAULT 'write',
    status TEXT NOT NULL DEFAULT 'active',
    locked_at INTEGER NOT NULL,
    released_at INTEGER,
    expires_at INTEGER,
    note TEXT DEFAULT '',
    UNIQUE(filepath, session_id)
);

INSERT OR IGNORE INTO agent_file_locks_v2
    SELECT lock_id, filepath, session_id, task_id, mode, status,
           locked_at, released_at, expires_at, note
    FROM agent_file_locks;

DROP TABLE IF EXISTS agent_file_locks;

ALTER TABLE agent_file_locks_v2 RENAME TO agent_file_locks;

CREATE INDEX IF NOT EXISTS idx_locks_filepath
    ON agent_file_locks(filepath, status);
"""

_MIGRATIONS: list[tuple[int, str]] = [
    (1, "init_agent_os"),
    (2, "fix_locks_unique_constraint"),
]

_MIGRATION_SQL: dict[int, str] = {
    1: _MIGRATION_1_SQL,
    2: _MIGRATION_2_SQL,
}


def apply_migrations(conn: sqlite3.Connection) -> None:
    """Apply all pending migrations. Idempotent — safe to call repeatedly."""
    # Bootstrap the migrations table without depending on it existing
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agent_os_migrations(
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at INTEGER NOT NULL
        )
    """)
    conn.commit()

    applied = {row["version"] for row in conn.execute(
        "SELECT version FROM agent_os_migrations"
    )}

    for version, name in _MIGRATIONS:
        if version in applied:
            continue
        sql = _MIGRATION_SQL[version]
        conn.executescript(sql)
        conn.execute(
            "INSERT INTO agent_os_migrations(version, name, applied_at) VALUES(?,?,?)",
            (version, name, int(time.time())),
        )
        conn.commit()
