-- Migration 0002: Knowledge graph nodes and edges
-- Applied to: ~/.ragd/ragd.db (RAGD primary store) and ~/.dominion/manifest.db
-- Note: These tables are also created by dominion_loader/graph.py at runtime.
-- This migration ensures they exist in the RAGD DB for cross-agent querying.

PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS kg_nodes(
    node_id    TEXT PRIMARY KEY,
    kind       TEXT NOT NULL,
    name       TEXT NOT NULL,
    filepath   TEXT NOT NULL DEFAULT '',
    language   TEXT NOT NULL DEFAULT 'unknown',
    line_start INTEGER NOT NULL DEFAULT 0,
    line_end   INTEGER NOT NULL DEFAULT 0,
    updated_at INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_kg_nodes_filepath
    ON kg_nodes(filepath);

CREATE INDEX IF NOT EXISTS idx_kg_nodes_kind
    ON kg_nodes(kind);

CREATE TABLE IF NOT EXISTS kg_edges(
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    from_id    TEXT NOT NULL,
    to_id      TEXT NOT NULL,
    relation   TEXT NOT NULL,
    filepath   TEXT NOT NULL DEFAULT '',
    created_at INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_kg_edges_from
    ON kg_edges(from_id);

CREATE INDEX IF NOT EXISTS idx_kg_edges_to
    ON kg_edges(to_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_kg_edges_unique
    ON kg_edges(from_id, to_id, relation);
