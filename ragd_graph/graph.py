from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class GraphStats:
    nodes: int
    edges: int
    by_relation: dict[str, int]


def default_db() -> Path:
    return Path(os.environ.get("RAGD_DB_PATH", str(Path.home() / ".ragd" / "ragd.db"))).expanduser()


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS kg_nodes(id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, name TEXT UNIQUE, filepath TEXT DEFAULT '', qualified_name TEXT DEFAULT '', docstring TEXT DEFAULT '', is_public INTEGER DEFAULT 1)")
    conn.execute("CREATE TABLE IF NOT EXISTS kg_edges(id INTEGER PRIMARY KEY AUTOINCREMENT, from_node TEXT, to_node TEXT, relation TEXT, filepath TEXT DEFAULT '', confidence REAL DEFAULT 1.0)")
    for table, column, ddl in [
        ("kg_nodes", "qualified_name", "qualified_name TEXT DEFAULT ''"),
        ("kg_nodes", "docstring", "docstring TEXT DEFAULT ''"),
        ("kg_nodes", "is_public", "is_public INTEGER DEFAULT 1"),
        ("kg_edges", "confidence", "confidence REAL DEFAULT 1.0"),
    ]:
        columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if column not in columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def _loads_array(value: str | None) -> list[str]:
    try:
        parsed = json.loads(value or "[]")
    except json.JSONDecodeError:
        return []
    return [str(item) for item in parsed] if isinstance(parsed, list) else []


def _upsert_node(conn: sqlite3.Connection, *, kind: str, name: str, filepath: str = "", qualified_name: str = "", docstring: str = "", is_public: int = 1) -> None:
    if not name:
        return
    conn.execute(
        """
        INSERT INTO kg_nodes(kind, name, filepath, qualified_name, docstring, is_public)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET kind=excluded.kind, filepath=excluded.filepath, qualified_name=excluded.qualified_name, docstring=excluded.docstring, is_public=excluded.is_public
        """,
        (kind, name, filepath, qualified_name, docstring, is_public),
    )


def _edge(conn: sqlite3.Connection, source: str, target: str, relation: str, filepath: str, confidence: float) -> None:
    if not source or not target:
        return
    conn.execute("INSERT INTO kg_edges(from_node, to_node, relation, filepath, confidence) VALUES (?, ?, ?, ?, ?)", (source, target, relation, filepath, confidence))


def build_graph(ragd_db: Path | None = None) -> GraphStats:
    path = Path(ragd_db or default_db())
    if not path.exists():
        return GraphStats(0, 0, {})
    conn = _connect(path)
    try:
        _ensure_schema(conn)
        conn.execute("DELETE FROM kg_nodes")
        conn.execute("DELETE FROM kg_edges")
        columns = {row[1] for row in conn.execute("PRAGMA table_info(chunks)").fetchall()}
        select = [
            "filepath",
            "symbol_name",
            "chunk_type",
            "COALESCE(qualified_name, symbol_name) AS qualified_name" if "qualified_name" in columns else "symbol_name AS qualified_name",
            "COALESCE(docstring, '') AS docstring" if "docstring" in columns else "'' AS docstring",
            "COALESCE(imports_json, '[]') AS imports_json" if "imports_json" in columns else "'[]' AS imports_json",
            "COALESCE(calls_json, '[]') AS calls_json" if "calls_json" in columns else "'[]' AS calls_json",
            "COALESCE(is_public, 1) AS is_public" if "is_public" in columns else "1 AS is_public",
        ]
        rows = conn.execute(f"SELECT {', '.join(select)} FROM chunks WHERE status='active'").fetchall()
        for row in rows:
            filepath = row["filepath"]
            file_node = f"file:{filepath}"
            _upsert_node(conn, kind="file", name=file_node, filepath=filepath)
            symbol = row["qualified_name"] or row["symbol_name"]
            if symbol:
                symbol_node = f"symbol:{symbol}"
                _upsert_node(conn, kind=row["chunk_type"] or "symbol", name=symbol_node, filepath=filepath, qualified_name=symbol, docstring=row["docstring"], is_public=int(row["is_public"]))
                _edge(conn, file_node, symbol_node, "defines", filepath, 1.0)
                for call in _loads_array(row["calls_json"]):
                    target = f"symbol:{call}"
                    _upsert_node(conn, kind="symbol_ref", name=target)
                    _edge(conn, symbol_node, target, "calls", filepath, 0.6)
            for imported in _loads_array(row["imports_json"]):
                target = f"import:{imported}"
                _upsert_node(conn, kind="import", name=target)
                _edge(conn, file_node, target, "imports", filepath, 0.8)
        conn.commit()
        return stats(path)
    finally:
        conn.close()


def stats(ragd_db: Path | None = None) -> GraphStats:
    path = Path(ragd_db or default_db())
    if not path.exists():
        return GraphStats(0, 0, {})
    conn = _connect(path)
    try:
        _ensure_schema(conn)
        nodes = conn.execute("SELECT COUNT(*) FROM kg_nodes").fetchone()[0]
        edges = conn.execute("SELECT COUNT(*) FROM kg_edges").fetchone()[0]
        by_relation = {row["relation"]: int(row["n"]) for row in conn.execute("SELECT relation, COUNT(*) AS n FROM kg_edges GROUP BY relation").fetchall()}
        return GraphStats(nodes=int(nodes), edges=int(edges), by_relation=by_relation)
    finally:
        conn.close()


def callers(symbol: str, ragd_db: Path | None = None, limit: int = 20) -> list[dict[str, Any]]:
    target = symbol if symbol.startswith("symbol:") else f"symbol:{symbol}"
    conn = _connect(Path(ragd_db or default_db()))
    try:
        _ensure_schema(conn)
        rows = conn.execute("SELECT from_node, filepath, confidence FROM kg_edges WHERE relation='calls' AND to_node=? LIMIT ?", (target, limit)).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def callees(symbol: str, ragd_db: Path | None = None, limit: int = 20) -> list[dict[str, Any]]:
    source = symbol if symbol.startswith("symbol:") else f"symbol:{symbol}"
    conn = _connect(Path(ragd_db or default_db()))
    try:
        _ensure_schema(conn)
        rows = conn.execute("SELECT to_node, filepath, confidence FROM kg_edges WHERE relation='calls' AND from_node=? LIMIT ?", (source, limit)).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def imports(filepath: str, ragd_db: Path | None = None, limit: int = 50) -> list[dict[str, Any]]:
    source = filepath if filepath.startswith("file:") else f"file:{filepath}"
    conn = _connect(Path(ragd_db or default_db()))
    try:
        _ensure_schema(conn)
        rows = conn.execute("SELECT to_node, confidence FROM kg_edges WHERE relation='imports' AND from_node=? LIMIT ?", (source, limit)).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def importers(import_name: str, ragd_db: Path | None = None, limit: int = 50) -> list[dict[str, Any]]:
    target = import_name if import_name.startswith("import:") else f"import:{import_name}"
    conn = _connect(Path(ragd_db or default_db()))
    try:
        _ensure_schema(conn)
        rows = conn.execute("SELECT from_node, filepath, confidence FROM kg_edges WHERE relation='imports' AND to_node=? LIMIT ?", (target, limit)).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
