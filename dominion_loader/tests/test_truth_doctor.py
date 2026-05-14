from __future__ import annotations

import sqlite3
from pathlib import Path

from dominion_loader.manifest import Manifest, ManifestEntry
from dominion_loader.truth_doctor import CmdResult, DoctorDeps, run_deep_doctor


def _deps(tmp_path: Path, *, http_json=None, run_cmd=None) -> DoctorDeps:
    root = tmp_path / "root"
    root.mkdir(exist_ok=True)
    manifest_path = tmp_path / "manifest.db"
    ragd_db_path = tmp_path / "ragd.db"
    cache_path = tmp_path / "cache"
    return DoctorDeps(
        root=root,
        manifest_path=manifest_path,
        ragd_db_path=ragd_db_path,
        cache_path=cache_path,
        ragd_url="http://ragd.test",
        http_json=http_json,
        run_cmd=run_cmd or (lambda cmd, timeout: CmdResult(0, "PASS")),
    )


def _write_manifest(path: Path, *, status: str = "deleted", repo_root: Path | None = None, relative_path: str = "gone.py") -> None:
    manifest = Manifest(path)
    root = str(repo_root or path.parent)
    manifest.upsert(
        ManifestEntry(
            document_id="doc-1",
            repo_root=root,
            relative_path=relative_path,
            file_class="code",
            language="python",
            content_hash="hash",
            mtime_ns=1,
            size=1,
            indexed_at=1,
            ragd_ingested=1,
            ragd_ingested_at=1,
            status=status,
        )
    )
    manifest.close()


def _write_ragd_db(path: Path, *, filepath: str, status: str = "active") -> None:
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE chunks(
            id INTEGER PRIMARY KEY,
            filepath TEXT,
            status TEXT,
            line_start INTEGER,
            line_end INTEGER,
            content_hash TEXT
        )
        """
    )
    conn.execute(
        "INSERT INTO chunks(filepath,status,line_start,line_end,content_hash) VALUES(?,?,?,?,?)",
        (filepath, status, 1, 2, "hash"),
    )
    conn.commit()
    conn.close()


def test_deep_doctor_reports_missing_query_metadata(tmp_path: Path) -> None:
    def fake_http(url, payload=None, timeout=5):
        if url.endswith("/health"):
            return {"ok": True, "data": {"status": "ok"}}
        return {"ok": True, "data": {"results": [{"chunk_id": 1, "filepath": "/repo/a.py"}]}}

    report = run_deep_doctor(deps=_deps(tmp_path, http_json=fake_http), max_sample=10)

    check = report["checks"]["query_metadata_contract"]
    assert check["status"] == "fail"
    assert "content_hash" in check["evidence"]["missing"]


def test_deep_doctor_detects_deleted_chunk_leak(tmp_path: Path) -> None:
    deps = _deps(tmp_path)
    deleted_path = str((tmp_path / "gone.py").resolve())
    _write_manifest(deps.manifest_path, repo_root=tmp_path, relative_path="gone.py")
    _write_ragd_db(deps.ragd_db_path, filepath=deleted_path)

    report = run_deep_doctor(deps=deps, offline=True, max_sample=10)

    check = report["checks"]["deleted_chunk_leaks"]
    assert check["status"] == "fail"
    assert check["evidence"]["leak_count"] == 1


def test_deep_doctor_reports_cache_corruption(tmp_path: Path) -> None:
    deps = _deps(tmp_path)
    bad_dir = deps.cache_path / "aa" / "bb"
    bad_dir.mkdir(parents=True)
    (bad_dir / "bad.cache").write_bytes(b"malformed-without-newline")

    report = run_deep_doctor(deps=deps, offline=True, max_sample=10)

    check = report["checks"]["cache_integrity"]
    assert check["status"] == "warn"
    assert check["evidence"]["corrupt"]


def test_deep_doctor_reports_temp_adapters(tmp_path: Path) -> None:
    deps = _deps(tmp_path)
    code_dir = deps.root / "dominion_ai"
    code_dir.mkdir()
    (code_dir / "adapter.py").write_text(
        'NOTE = "TEMP_ADAPTER(agent-x): remove when producer metadata is deployed."\n',
        encoding="utf-8",
    )

    report = run_deep_doctor(deps=deps, offline=True, max_sample=10)

    check = report["checks"]["temp_adapters"]
    assert check["status"] == "warn"
    assert check["evidence"]["count"] == 1


def test_deep_doctor_offline_skips_ragd(tmp_path: Path) -> None:
    report = run_deep_doctor(deps=_deps(tmp_path), offline=True, max_sample=10)

    assert report["checks"]["ragd_reachable"]["status"] == "skip"
    assert report["checks"]["query_metadata_contract"]["status"] == "skip"


def test_shallow_doctor_parser_still_accepts_legacy_flags() -> None:
    from scripts.dominion_cli import build_parser

    args = build_parser().parse_args(["doctor", "--json"])
    assert args.json is True
    assert getattr(args, "deep") is False
