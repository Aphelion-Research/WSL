"""Deep truth doctor for real Dominion/RAGD state.

Deep mode inspects the actual manifest, cache, RAGD metadata contract, and
live deletion invariants. It does not use fresh temp fixtures.
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import URLError
from urllib.request import Request, urlopen

from dominion_loader.cache import Cache
from dominion_loader.ignore import policy_hash

STATUS_ORDER = {"pass": 0, "skip": 1, "warn": 2, "fail": 3}
VRAM_SAFE_CEILING = 3_500_000_000
QUERY_METADATA_FIELDS = {"chunk_id", "filepath", "content_hash", "repo_root", "status", "indexed_at", "modified_at"}
TEMP_ADAPTER_DIRS = ("dominion_ai", "local_llm", "dominion_loader", "scripts")
TEMP_ADAPTER_PATTERN = re.compile(r"TEMP_ADAPTER\([^)]+\):")


@dataclass(frozen=True)
class CmdResult:
    returncode: int
    output: str


@dataclass
class DoctorDeps:
    root: Path = field(default_factory=lambda: Path(os.environ.get("DOMINION_ROOT", str(Path.home() / "Dominion"))).expanduser())
    manifest_path: Path = field(default_factory=lambda: Path(os.environ.get("DOMINION_HOME", str(Path.home() / ".dominion"))) / "manifest.db")
    ragd_db_path: Path = field(default_factory=lambda: Path(os.environ.get("RAGD_DB_PATH", str(Path.home() / ".ragd" / "ragd.db"))).expanduser())
    cache_path: Path = field(default_factory=lambda: Path(os.environ.get("DOMINION_HOME", str(Path.home() / ".dominion"))) / "cache")
    ragd_url: str = field(default_factory=lambda: os.environ.get("RAGD_URL", "http://127.0.0.1:7474").rstrip("/"))
    http_json: Callable[[str, dict[str, Any] | None, int], dict[str, Any]] | None = None
    run_cmd: Callable[[list[str], int], CmdResult] | None = None


def run_deep_doctor(*, deps: DoctorDeps | None = None, offline: bool = False, max_sample: int = 200) -> dict[str, Any]:
    """Run deep state checks and return machine-auditable JSON data."""
    deps = deps or DoctorDeps()
    root = deps.root.expanduser().resolve()
    checks: dict[str, dict[str, Any]] = {}

    checks["ragd_reachable"] = _check_ragd_reachable(deps, offline)
    checks["query_metadata_contract"] = _check_query_metadata_contract(deps, offline)
    checks["manifest_readable"] = _check_manifest_readable(deps.manifest_path)
    checks["deleted_chunk_leaks"] = _check_deleted_chunk_leaks(deps.manifest_path, deps.ragd_db_path, max_sample)
    checks["active_manifest_without_chunks"] = _check_active_manifest_without_chunks(deps.manifest_path, deps.ragd_db_path, max_sample)
    checks["cache_integrity"] = _check_cache_integrity(deps.cache_path)
    checks["ignore_policy_alignment"] = _check_ignore_policy_alignment(deps, checks["ragd_reachable"], offline)
    checks["domdata_guard"] = _check_domdata_guard(deps, root)
    checks["llm_governor_truth"] = _check_llm_governor_truth()
    checks["temp_adapters"] = _check_temp_adapters(root)
    checks["duplicate_active_chunks"] = _check_duplicate_active_chunks(deps.ragd_db_path)
    checks["orphan_active_chunks"] = _check_orphan_active_chunks(deps.ragd_db_path, max_sample)

    return {
        "overall": _overall(checks),
        "mode": "deep",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "root": str(root),
        "checks": checks,
    }


def _check(status: str, severity: str, detail: str, *, remedy: str | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"status": status, "severity": severity, "detail": detail, "remedy": remedy, "evidence": evidence or {}}


def _overall(checks: dict[str, dict[str, Any]]) -> str:
    worst = max((STATUS_ORDER.get(check.get("status", "fail"), 3) for check in checks.values()), default=0)
    if worst >= STATUS_ORDER["fail"]:
        return "fail"
    if worst >= STATUS_ORDER["warn"]:
        return "warn"
    return "ok"


def _http_json(deps: DoctorDeps, url: str, payload: dict[str, Any] | None = None, timeout: int = 5) -> dict[str, Any]:
    if deps.http_json is not None:
        return deps.http_json(url, payload, timeout)
    try:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        req = Request(url, data=data, headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return {"ok": True, "status_code": response.status, "data": json.loads(body) if body else {}}
    except (OSError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": str(exc)}


def _run_cmd(deps: DoctorDeps, cmd: list[str], timeout: int = 30) -> CmdResult:
    if deps.run_cmd is not None:
        return deps.run_cmd(cmd, timeout)
    try:
        result = subprocess.run(cmd, cwd=deps.root, text=True, capture_output=True, timeout=timeout, check=False)
        output = (result.stdout or result.stderr or "").strip()
        return CmdResult(result.returncode, output)
    except Exception as exc:
        return CmdResult(124, f"unavailable: {exc}")


def _connect_ro(path: Path) -> sqlite3.Connection:
    uri = f"file:{path.expanduser()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _check_ragd_reachable(deps: DoctorDeps, offline: bool) -> dict[str, Any]:
    if offline:
        return _check("skip", "critical", "offline mode requested; RAGD reachability not checked")
    health = _http_json(deps, f"{deps.ragd_url}/health")
    if not health.get("ok"):
        return _check("fail", "critical", "RAGD /health is unreachable", remedy="Start RAGD or pass --offline.", evidence=health)
    data = health.get("data", {})
    if data.get("status") == "ok" or data.get("ok") is True:
        return _check("pass", "critical", "RAGD /health returned status ok", evidence={"health": data})
    return _check("fail", "critical", "RAGD /health returned a non-ok payload", evidence={"health": data})


def _check_query_metadata_contract(deps: DoctorDeps, offline: bool) -> dict[str, Any]:
    if offline:
        return _check("skip", "critical", "offline mode requested; query metadata contract not checked")
    response = _http_json(deps, f"{deps.ragd_url}/query", {"q": "agent handoff", "top_k": 1, "mode": "hybrid"})
    if not response.get("ok"):
        return _check("fail", "critical", "RAGD /query is unreachable", evidence=response)
    results = response.get("data", {}).get("results", [])
    if not results:
        return _check("warn", "high", "RAGD query returned no results; metadata contract could not be sampled", evidence={"query": "agent handoff"})
    result = results[0]
    missing = sorted(field for field in QUERY_METADATA_FIELDS if field not in result)
    if missing:
        return _check("fail", "high", "RAGD query result is missing required identity metadata", remedy="Deploy RAGD metadata contract patch and restart daemon.", evidence={"missing": missing, "result_keys": sorted(result.keys())})
    return _check("pass", "high", "RAGD query result includes required identity metadata", evidence={"fields": sorted(QUERY_METADATA_FIELDS)})


def _check_manifest_readable(manifest_path: Path) -> dict[str, Any]:
    if not manifest_path.exists():
        return _check("skip", "medium", "manifest.db is missing; no scan may have run", evidence={"path": str(manifest_path)})
    try:
        with _connect_ro(manifest_path) as conn:
            active = conn.execute("SELECT COUNT(*) FROM file_manifest WHERE status='active'").fetchone()[0]
            deleted = conn.execute("SELECT COUNT(*) FROM file_manifest WHERE status='deleted'").fetchone()[0]
            ingested = conn.execute("SELECT COUNT(*) FROM file_manifest WHERE ragd_ingested=1 AND status='active'").fetchone()[0]
        return _check("pass", "medium", "manifest.db is readable", evidence={"path": str(manifest_path), "active": active, "deleted": deleted, "ragd_ingested": ingested})
    except sqlite3.Error as exc:
        return _check("fail", "high", "manifest.db cannot be read", remedy="Inspect or rebuild the loader manifest.", evidence={"path": str(manifest_path), "error": str(exc)})


def _check_deleted_chunk_leaks(manifest_path: Path, ragd_db_path: Path, max_sample: int) -> dict[str, Any]:
    if not manifest_path.exists() or not ragd_db_path.exists():
        return _check("skip", "high", "manifest or RAGD DB missing; deleted chunk leaks not checked", evidence={"manifest": str(manifest_path), "ragd_db": str(ragd_db_path)})
    leaks: list[dict[str, Any]] = []
    sampled = 0
    try:
        with _connect_ro(manifest_path) as manifest_conn, _connect_ro(ragd_db_path) as ragd_conn:
            rows = manifest_conn.execute("SELECT repo_root, relative_path FROM file_manifest WHERE status='deleted' LIMIT ?", (max_sample,)).fetchall()
            sampled = len(rows)
            for row in rows:
                path = str((Path(row["repo_root"]) / row["relative_path"]).resolve())
                count = ragd_conn.execute("SELECT COUNT(*) FROM chunks WHERE filepath=? AND status='active'", (path,)).fetchone()[0]
                if count:
                    leaks.append({"filepath": path, "active_chunks": count})
    except sqlite3.Error as exc:
        return _check("fail", "high", "deleted chunk leak scan failed", evidence={"error": str(exc)})
    if leaks:
        return _check("fail", "critical", "deleted manifest entries still have active RAGD chunks", remedy="Run dominion scan after deploying RAGD /index/delete.", evidence={"leak_count": len(leaks), "sampled": sampled, "examples": leaks[:5]})
    return _check("pass", "critical", "no active RAGD chunks found for sampled deleted manifest entries", evidence={"sampled": sampled, "max_sample": max_sample})


def _check_active_manifest_without_chunks(manifest_path: Path, ragd_db_path: Path, max_sample: int) -> dict[str, Any]:
    if not manifest_path.exists() or not ragd_db_path.exists():
        return _check("skip", "medium", "manifest or RAGD DB missing; active manifest chunk coverage not checked")
    missing: list[str] = []
    sampled = 0
    try:
        with _connect_ro(manifest_path) as manifest_conn, _connect_ro(ragd_db_path) as ragd_conn:
            rows = manifest_conn.execute(
                "SELECT repo_root, relative_path FROM file_manifest WHERE status='active' AND ragd_ingested=1 LIMIT ?",
                (max_sample,),
            ).fetchall()
            sampled = len(rows)
            for row in rows:
                path = str((Path(row["repo_root"]) / row["relative_path"]).resolve())
                count = ragd_conn.execute("SELECT COUNT(*) FROM chunks WHERE filepath=? AND status='active'", (path,)).fetchone()[0]
                if count == 0:
                    missing.append(path)
    except sqlite3.Error as exc:
        return _check("fail", "medium", "active manifest chunk coverage scan failed", evidence={"error": str(exc)})
    if missing:
        return _check("warn", "medium", "some active ingested manifest entries have no active RAGD chunks", remedy="Run dominion scan or inspect RAGD ingestion failures.", evidence={"missing_count": len(missing), "sampled": sampled, "examples": missing[:5]})
    return _check("pass", "medium", "sampled active ingested manifest entries have active RAGD chunks", evidence={"sampled": sampled, "max_sample": max_sample})


def _check_cache_integrity(cache_path: Path) -> dict[str, Any]:
    try:
        cache = Cache(cache_path)
        corrupt = cache.verify()
        stats = cache.stats()
    except Exception as exc:
        return _check("fail", "medium", "cache cannot be read", evidence={"path": str(cache_path), "error": str(exc)})
    evidence = {"path": str(cache_path), "stats": stats, "corrupt": corrupt[:5]}
    if corrupt or stats.get("corrupt", 0):
        return _check("warn", "medium", "cache has corrupt or quarantined entries", remedy="Run dominion cache verify; corrupt entries are ignored.", evidence=evidence)
    return _check("pass", "medium", "cache verify found no corrupt entries", evidence=evidence)


def _check_ignore_policy_alignment(deps: DoctorDeps, ragd_reachable: dict[str, Any], offline: bool) -> dict[str, Any]:
    python_hash = policy_hash()
    if offline or ragd_reachable.get("status") == "skip":
        return _check("skip", "medium", "offline mode requested; ignore policy alignment not checked", evidence={"python_policy_hash": python_hash})
    health = ragd_reachable.get("evidence", {}).get("health", {})
    ragd_hash = health.get("ignore_policy_hash")
    if not ragd_hash:
        return _check("warn", "medium", "RAGD does not expose ignore_policy_hash; alignment is not provable", remedy="Expose RAGD ignore_policy_hash or consume config/dominion_ignore_policy.json.", evidence={"python_policy_hash": python_hash})
    if ragd_hash != python_hash:
        return _check("fail", "high", "Python loader and RAGD ignore policy hashes differ", evidence={"python_policy_hash": python_hash, "ragd_policy_hash": ragd_hash})
    return _check("pass", "medium", "Python loader and RAGD ignore policy hashes match", evidence={"policy_hash": python_hash})


def _check_domdata_guard(deps: DoctorDeps, root: Path) -> dict[str, Any]:
    cmd = [sys.executable, str(root / "domdata" / "check_no_trading.py")]
    result = _run_cmd(deps, cmd, timeout=30)
    if result.returncode == 0:
        return _check("pass", "critical", "domdata forbidden-token scanner passed", evidence={"command": " ".join(cmd), "output": result.output[:1000]})
    return _check("fail", "critical", "domdata forbidden-token scanner failed", remedy="Remove forbidden trading tokens outside allowlisted safety tests.", evidence={"command": " ".join(cmd), "returncode": result.returncode, "output": result.output[:2000]})


def _check_llm_governor_truth() -> dict[str, Any]:
    try:
        from local_llm.registry import MODEL_REGISTRY
        from local_llm.governor import registry_truth
    except Exception as exc:
        return _check("skip", "medium", "local_llm registry is unavailable", evidence={"error": str(exc)})
    truth = registry_truth(MODEL_REGISTRY)
    if truth["status"] == "fail":
        return _check("fail", "high", "a local LLM profile named safe exceeds the 3.5 GB VRAM ceiling", remedy="Rename risky profiles or make 4 GB default retrieve-only.", evidence=truth)
    if truth["status"] == "warn":
        return _check("warn", "medium", "no automatic generation profile is available under the 3.5 GB VRAM ceiling; retrieve-only fallback is explicit", evidence=truth)
    return _check("pass", "medium", "local LLM registry has no unsafe safe profiles", evidence=truth)


def _check_temp_adapters(root: Path) -> dict[str, Any]:
    adapters: list[dict[str, Any]] = []
    unlabeled: list[dict[str, Any]] = []
    for dirname in TEMP_ADAPTER_DIRS:
        base = root / dirname
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix not in {".py", ".md", ".txt", ".json", ".yaml", ".yml"}:
                continue
            try:
                for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
                    if not TEMP_ADAPTER_PATTERN.search(line):
                        continue
                    item = {"path": str(path.relative_to(root)), "line": lineno, "text": line.strip()[:240]}
                    adapters.append(item)
                    lower = line.lower()
                    if "temp_adapter(" not in lower or ("remove" not in lower and "removal" not in lower):
                        unlabeled.append(item)
            except OSError:
                continue
    if unlabeled:
        return _check("fail", "medium", "unlabeled TEMP_ADAPTER markers found", remedy="Label owner and removal condition for each adapter.", evidence={"count": len(adapters), "unlabeled": unlabeled[:10]})
    if adapters:
        return _check("warn", "low", "TEMP_ADAPTER markers remain but are labeled", evidence={"count": len(adapters), "examples": adapters[:10]})
    return _check("pass", "low", "no TEMP_ADAPTER markers found")


def _check_duplicate_active_chunks(ragd_db_path: Path) -> dict[str, Any]:
    if not ragd_db_path.exists():
        return _check("skip", "medium", "RAGD DB missing; duplicate active chunks not checked", evidence={"ragd_db": str(ragd_db_path)})
    try:
        with _connect_ro(ragd_db_path) as conn:
            rows = conn.execute(
                """
                SELECT filepath, line_start, line_end, content_hash, COUNT(*) AS n
                FROM chunks
                WHERE status='active'
                GROUP BY filepath, line_start, line_end, content_hash
                HAVING n > 1
                LIMIT 20
                """
            ).fetchall()
    except sqlite3.Error as exc:
        return _check("fail", "medium", "duplicate active chunk scan failed", evidence={"error": str(exc)})
    if rows:
        examples = [dict(row) for row in rows]
        return _check("warn", "medium", "duplicate active chunk identities found", remedy="Run an index repair that marks older duplicates deleted.", evidence={"duplicate_groups_sampled": len(examples), "examples": examples})
    return _check("pass", "medium", "no duplicate active chunk identities found")


def _check_orphan_active_chunks(ragd_db_path: Path, max_sample: int) -> dict[str, Any]:
    if not ragd_db_path.exists():
        return _check("skip", "medium", "RAGD DB missing; orphan active chunks not checked", evidence={"ragd_db": str(ragd_db_path)})
    orphans: list[str] = []
    sampled = 0
    try:
        with _connect_ro(ragd_db_path) as conn:
            rows = conn.execute("SELECT DISTINCT filepath FROM chunks WHERE status='active' LIMIT ?", (max_sample,)).fetchall()
            sampled = len(rows)
            for row in rows:
                filepath = row["filepath"]
                if filepath and not Path(filepath).exists():
                    orphans.append(filepath)
    except sqlite3.Error as exc:
        return _check("fail", "medium", "orphan active chunk scan failed", evidence={"error": str(exc)})
    if orphans:
        return _check("warn", "medium", "active RAGD chunks reference missing files", remedy="Run dominion scan after RAGD deletion propagation is deployed.", evidence={"orphan_count": len(orphans), "sampled": sampled, "examples": orphans[:10]})
    return _check("pass", "medium", "sampled active RAGD chunks reference existing files", evidence={"sampled": sampled, "max_sample": max_sample})
