#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sqlite3
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_DB = Path(os.environ.get("RAGD_DB", str(Path.home() / ".ragd" / "ragd.db"))).expanduser()


@dataclass(frozen=True)
class Report:
    db_path: str
    ok: bool
    tables: list[str]
    chunks_total: int | None
    chunks_active: int | None
    chunks_deleted: int | None
    duplicate_hash_groups: int | None
    duplicate_hash_rows: int | None
    top_files: list[dict[str, Any]]
    notes: list[str]


def _connect(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise FileNotFoundError(f"db not found: {db_path}")
    uri = f"file:{db_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _tables(conn: sqlite3.Connection) -> list[str]:
    return [r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]


def _table_has(conn: sqlite3.Connection, table: str, col: str) -> bool:
    cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
    return col in cols


def build_report(conn: sqlite3.Connection, db_path: Path) -> Report:
    tables = _tables(conn)
    notes: list[str] = []

    chunks_total = chunks_active = chunks_deleted = None
    duplicate_groups = duplicate_rows = None
    top_files: list[dict[str, Any]] = []

    if "chunks" not in tables:
        notes.append("missing table: chunks (not a ragd db?)")
        return Report(
            db_path=str(db_path),
            ok=False,
            tables=tables,
            chunks_total=None,
            chunks_active=None,
            chunks_deleted=None,
            duplicate_hash_groups=None,
            duplicate_hash_rows=None,
            top_files=[],
            notes=notes,
        )

    chunks_total = int(conn.execute("SELECT COUNT(*) AS n FROM chunks").fetchone()["n"])
    if _table_has(conn, "chunks", "status"):
        chunks_active = int(conn.execute("SELECT COUNT(*) AS n FROM chunks WHERE status = 'active'").fetchone()["n"])
        chunks_deleted = int(conn.execute("SELECT COUNT(*) AS n FROM chunks WHERE status != 'active'").fetchone()["n"])
    else:
        notes.append("chunks.status missing; active/deleted counts unavailable")

    if _table_has(conn, "chunks", "content_hash"):
        rows = list(
            conn.execute(
                """
                SELECT content_hash, COUNT(*) AS n
                FROM chunks
                WHERE content_hash IS NOT NULL AND content_hash != ''
                GROUP BY content_hash
                HAVING COUNT(*) > 1
                ORDER BY n DESC
                LIMIT 200
                """
            )
        )
        duplicate_groups = len(rows)
        duplicate_rows = int(sum(int(r["n"]) for r in rows))
    else:
        notes.append("chunks.content_hash missing; duplicate detection unavailable")

    if _table_has(conn, "chunks", "filepath"):
        for row in conn.execute(
            """
            SELECT filepath, COUNT(*) AS n
            FROM chunks
            GROUP BY filepath
            ORDER BY n DESC
            LIMIT 20
            """
        ):
            top_files.append({"filepath": row["filepath"], "chunks": int(row["n"])})

    if "kv_store" in tables:
        try:
            schema_version = conn.execute("SELECT value FROM kv_store WHERE key='schema_version'").fetchone()
            if schema_version:
                notes.append(f"schema_version={schema_version['value']}")
        except Exception:
            pass

    return Report(
        db_path=str(db_path),
        ok=True,
        tables=tables,
        chunks_total=chunks_total,
        chunks_active=chunks_active,
        chunks_deleted=chunks_deleted,
        duplicate_hash_groups=duplicate_groups,
        duplicate_hash_rows=duplicate_rows,
        top_files=top_files,
        notes=notes,
    )


def cleanup_duplicates(conn: sqlite3.Connection, *, dry_run: bool) -> dict[str, Any]:
    if "chunks" not in set(_tables(conn)):
        return {"ok": False, "error": "missing table: chunks"}
    for col in ("id", "content_hash"):
        if not _table_has(conn, "chunks", col):
            return {"ok": False, "error": f"chunks missing column: {col}"}
    if not _table_has(conn, "chunks", "status"):
        return {"ok": False, "error": "chunks.status missing; cannot safely apply cleanup"}

    dup_rows = list(
        conn.execute(
            """
            SELECT content_hash, GROUP_CONCAT(id) AS ids, COUNT(*) AS n
            FROM chunks
            WHERE status = 'active' AND content_hash IS NOT NULL AND content_hash != ''
            GROUP BY content_hash
            HAVING COUNT(*) > 1
            ORDER BY n DESC
            LIMIT 500
            """
        )
    )
    groups = len(dup_rows)
    candidate_ids: list[int] = []
    for row in dup_rows:
        ids = [int(x) for x in str(row["ids"]).split(",") if x]
        ids.sort()
        candidate_ids.extend(ids[1:])  # keep smallest id

    summary = Counter()
    if candidate_ids:
        placeholders = ",".join("?" for _ in candidate_ids)
        for r in conn.execute(f"SELECT filepath FROM chunks WHERE id IN ({placeholders})", candidate_ids):
            summary[str(r["filepath"])] += 1

    planned = {
        "ok": True,
        "dry_run": dry_run,
        "duplicate_groups_considered": groups,
        "candidates": len(candidate_ids),
        "example_ids": candidate_ids[:20],
        "top_files": [{"filepath": fp, "candidates": n} for fp, n in summary.most_common(10)],
        "criteria": "active chunks grouped by content_hash; keep smallest id per group; mark others deleted",
    }
    if dry_run or not candidate_ids:
        return planned

    conn.execute("BEGIN")
    placeholders = ",".join("?" for _ in candidate_ids)
    conn.execute(f"UPDATE chunks SET status='deleted' WHERE id IN ({placeholders})", candidate_ids)
    conn.commit()
    planned["applied"] = True
    return planned


def cmd_report(args: argparse.Namespace) -> int:
    try:
        conn = _connect(Path(args.db))
    except Exception as exc:
        out = {"ok": False, "error": str(exc), "db": args.db}
        print(json.dumps(out, indent=2, sort_keys=True) if args.json else out["error"])
        return 2
    with conn:
        report = build_report(conn, Path(args.db))
    payload = report.__dict__
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"RAGD maintenance report: {report.db_path}")
        print(f"tables: {', '.join(report.tables)}")
        print(f"chunks_total: {report.chunks_total}")
        if report.chunks_active is not None:
            print(f"chunks_active: {report.chunks_active} chunks_deleted: {report.chunks_deleted}")
        if report.duplicate_hash_groups is not None:
            print(f"duplicate_hash_groups: {report.duplicate_hash_groups} duplicate_hash_rows: {report.duplicate_hash_rows}")
        if report.top_files:
            print("top_files:")
            for item in report.top_files[:10]:
                print(f"  {item['chunks']:6d} {item['filepath']}")
        for note in report.notes:
            print(f"note: {note}")
    return 0 if report.ok else 1


def cmd_cleanup_duplicates(args: argparse.Namespace) -> int:
    db_path = Path(args.db)
    if not db_path.exists():
        print(json.dumps({"ok": False, "error": f"db not found: {db_path}"}, indent=2, sort_keys=True))
        return 2
    uri = f"file:{db_path}?mode={'ro' if args.dry_run else 'rw'}"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    result = cleanup_duplicates(conn, dry_run=bool(args.dry_run))
    print(json.dumps(result, indent=2, sort_keys=True) if args.json else json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok") else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ragd-maint", description="RAGD maintenance and memory health tools (safe by default)")
    p.add_argument("--db", default=str(DEFAULT_DB), help="Path to ragd sqlite db (default: ~/.ragd/ragd.db or $RAGD_DB)")
    sub = p.add_subparsers(dest="command", required=True)

    r = sub.add_parser("report", help="Inspect schema + chunk health (non-destructive)")
    r.add_argument("--json", action="store_true")
    r.set_defaults(func=cmd_report)

    c = sub.add_parser("cleanup-duplicates", help="Plan or apply duplicate cleanup (status=deleted, never hard delete)")
    c.add_argument("--dry-run", action="store_true", help="Default; only prints plan")
    c.add_argument("--apply", action="store_true", help="Apply the plan (marks duplicates status=deleted)")
    c.add_argument("--json", action="store_true")
    c.set_defaults(func=cmd_cleanup_duplicates)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "cleanup-duplicates":
        if not args.apply:
            args.dry_run = True
        elif args.apply:
            args.dry_run = False
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
