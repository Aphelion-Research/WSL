"""Repo knowledge graph data layer for dominion_loader (S02/F01).

SQLite tables: kg_nodes, kg_edges.
Builds the graph from RAGD's chunks (metadata_json) and loader's manifest.

Agent 2 owns the query/UX layer. This module owns the data ingest and schema.
INTERFACE(agent-1): KnowledgeGraph class  (Agent 2 builds query layer on top)
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional


@dataclass(frozen=True)
class KGNode:
    node_id: str     # sha256[:16] of (kind, name, filepath)
    kind: str        # "file" | "symbol" | "test" | "config" | "doc" | "chunk"
    name: str
    filepath: str
    language: str
    line_start: int
    line_end: int


@dataclass(frozen=True)
class KGEdge:
    from_id: str
    to_id: str
    relation: str    # "imports" | "defines" | "references" | "covers" | "configures"
    filepath: str


class KnowledgeGraph:
    """SQLite-backed knowledge graph.

    Schema lives in the manifest.db under kg_nodes/kg_edges tables.
    Ingest hook: builds graph from RAGD chunk metadata_json.
    """

    def __init__(self, db_path: Path | str | None = None) -> None:
        if db_path is None:
            dominion_home = Path(os.environ.get("DOMINION_HOME", str(Path.home() / ".dominion")))
            db_path = dominion_home / "manifest.db"
        self._db_path = Path(db_path)
        self._conn = sqlite3.connect(str(self._db_path), isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript("""
            PRAGMA journal_mode=WAL;

            CREATE TABLE IF NOT EXISTS kg_nodes(
                node_id   TEXT PRIMARY KEY,
                kind      TEXT NOT NULL,
                name      TEXT NOT NULL,
                filepath  TEXT NOT NULL DEFAULT '',
                language  TEXT NOT NULL DEFAULT 'unknown',
                line_start INTEGER NOT NULL DEFAULT 0,
                line_end   INTEGER NOT NULL DEFAULT 0,
                updated_at INTEGER NOT NULL DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_kg_nodes_filepath
                ON kg_nodes(filepath);

            CREATE INDEX IF NOT EXISTS idx_kg_nodes_kind
                ON kg_nodes(kind);

            CREATE TABLE IF NOT EXISTS kg_edges(
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                from_id   TEXT NOT NULL,
                to_id     TEXT NOT NULL,
                relation  TEXT NOT NULL,
                filepath  TEXT NOT NULL DEFAULT '',
                created_at INTEGER NOT NULL DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_kg_edges_from
                ON kg_edges(from_id);

            CREATE INDEX IF NOT EXISTS idx_kg_edges_to
                ON kg_edges(to_id);

            CREATE UNIQUE INDEX IF NOT EXISTS idx_kg_edges_unique
                ON kg_edges(from_id, to_id, relation);
        """)

    # ------------------------------------------------------------------
    # Ingest
    # ------------------------------------------------------------------
    def add_node(self, node: KGNode) -> None:
        """Upsert a knowledge graph node."""
        now = int(time.time())
        self._conn.execute(
            """
            INSERT OR REPLACE INTO kg_nodes
                (node_id, kind, name, filepath, language, line_start, line_end, updated_at)
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (node.node_id, node.kind, node.name, node.filepath,
             node.language, node.line_start, node.line_end, now),
        )
        self._conn.commit()

    def add_edge(self, edge: KGEdge) -> None:
        """Insert a knowledge graph edge (idempotent on unique constraint)."""
        now = int(time.time())
        self._conn.execute(
            """
            INSERT OR IGNORE INTO kg_edges(from_id, to_id, relation, filepath, created_at)
            VALUES(?,?,?,?,?)
            """,
            (edge.from_id, edge.to_id, edge.relation, edge.filepath, now),
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Query primitives
    # ------------------------------------------------------------------
    def get_node(self, node_id: str) -> Optional[KGNode]:
        """Retrieve a single node by ID, or None if not found."""
        row = self._conn.execute(
            "SELECT * FROM kg_nodes WHERE node_id=?", (node_id,)
        ).fetchone()
        if row is None:
            return None
        return KGNode(
            node_id=row["node_id"],
            kind=row["kind"],
            name=row["name"],
            filepath=row["filepath"],
            language=row["language"],
            line_start=row["line_start"],
            line_end=row["line_end"],
        )

    def list_nodes(self, *, kind: Optional[str] = None) -> list[KGNode]:
        """Return all nodes, optionally filtered by kind."""
        if kind:
            rows = self._conn.execute(
                "SELECT * FROM kg_nodes WHERE kind=? ORDER BY node_id", (kind,)
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM kg_nodes ORDER BY node_id"
            ).fetchall()
        return [
            KGNode(
                node_id=r["node_id"],
                kind=r["kind"],
                name=r["name"],
                filepath=r["filepath"],
                language=r["language"],
                line_start=r["line_start"],
                line_end=r["line_end"],
            )
            for r in rows
        ]

    def stats(self) -> dict[str, int]:
        """Return node and edge counts."""
        nodes = self._conn.execute("SELECT COUNT(*) FROM kg_nodes").fetchone()[0]
        edges = self._conn.execute("SELECT COUNT(*) FROM kg_edges").fetchone()[0]
        by_kind: dict[str, int] = {}
        for row in self._conn.execute(
            "SELECT kind, COUNT(*) AS n FROM kg_nodes GROUP BY kind ORDER BY n DESC"
        ):
            by_kind[row["kind"]] = row["n"]
        return {"nodes": nodes, "edges": edges, "by_kind": by_kind}  # type: ignore[return-value]

    def neighbors(self, node_id: str, *, relation: Optional[str] = None) -> list[str]:
        """Return node_ids directly connected to node_id."""
        if relation:
            rows = self._conn.execute(
                "SELECT to_id FROM kg_edges WHERE from_id=? AND relation=?",
                (node_id, relation),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT to_id FROM kg_edges WHERE from_id=?",
                (node_id,),
            ).fetchall()
        return [r[0] for r in rows]

    def close(self) -> None:
        self._conn.close()


def ingest_from_ragd(kg: KnowledgeGraph, ragd_db_path: Path | str) -> dict[str, int]:
    """Build the knowledge graph from RAGD's chunks table.

    Reads metadata_json to extract imports, calls, symbol_name, chunk_type.
    This is a read-only scan of the RAGD database.

    ASSUMPTION(agent-1): RAGD db at ~/.ragd/ragd.db
    """
    import hashlib

    ragd_path = Path(ragd_db_path)
    if not ragd_path.exists():
        return {"nodes": 0, "edges": 0, "error": "ragd_db_not_found"}

    uri = f"file:{ragd_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row

    nodes_added = 0
    edges_added = 0

    try:
        rows = conn.execute(
            """
            SELECT filepath, lang, chunk_type, symbol_name,
                   line_start, line_end, metadata_json, content_hash
            FROM chunks
            WHERE status='active'
            ORDER BY filepath, line_start
            """
        ).fetchall()
    except sqlite3.OperationalError:
        conn.close()
        return {"nodes": 0, "edges": 0, "error": "schema_error"}
    finally:
        conn.close()

    def make_id(kind: str, name: str, filepath: str) -> str:
        raw = f"{kind}:{name}:{filepath}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    for row in rows:
        filepath = row["filepath"] or ""
        lang = row["lang"] or "unknown"
        symbol = row["symbol_name"] or ""
        chunk_type = row["chunk_type"] or "block"
        line_start = row["line_start"] or 0
        line_end = row["line_end"] or 0

        # File node
        file_id = make_id("file", filepath, filepath)
        kg.add_node(KGNode(
            node_id=file_id,
            kind="file",
            name=filepath,
            filepath=filepath,
            language=lang,
            line_start=0,
            line_end=0,
        ))
        nodes_added += 1

        # Symbol node (if named)
        if symbol and chunk_type in ("function", "method", "class"):
            sym_id = make_id("symbol", symbol, filepath)
            kg.add_node(KGNode(
                node_id=sym_id,
                kind="symbol",
                name=symbol,
                filepath=filepath,
                language=lang,
                line_start=line_start,
                line_end=line_end,
            ))
            nodes_added += 1
            kg.add_edge(KGEdge(
                from_id=file_id, to_id=sym_id,
                relation="defines", filepath=filepath,
            ))
            edges_added += 1

        # Import edges from metadata_json
        try:
            meta = json.loads(row["metadata_json"] or "{}")
            imports = meta.get("imports", [])
            for imp in imports:
                imp_id = make_id("file", imp, imp)
                kg.add_node(KGNode(
                    node_id=imp_id,
                    kind="file",
                    name=imp,
                    filepath=imp,
                    language="unknown",
                    line_start=0,
                    line_end=0,
                ))
                kg.add_edge(KGEdge(
                    from_id=file_id, to_id=imp_id,
                    relation="imports", filepath=filepath,
                ))
                edges_added += 1
        except (json.JSONDecodeError, KeyError):
            pass

    return {"nodes": nodes_added, "edges": edges_added}
