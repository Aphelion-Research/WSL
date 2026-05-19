#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


ROOT = Path(
    os.environ.get("DOMINION_ROOT")
    or str(Path(__file__).resolve().parents[1])
).expanduser()
RAGD = os.environ.get("RAGD_URL", "http://127.0.0.1:7474").rstrip("/")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def run(cmd: list[str], timeout: int = 10) -> tuple[int, str]:
    try:
        result = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout, check=False)
        return result.returncode, (result.stdout or result.stderr or "").strip()
    except Exception as exc:
        return 124, f"unavailable: {exc}"


def http_json(url: str, payload: dict | None = None, timeout: int = 5) -> dict:
    try:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(url, data=data, headers={"Content-Type": "application/json"})
        with urlopen(request, timeout=timeout) as response:
            return {"ok": True, "status_code": response.status, "data": json.loads(response.read().decode("utf-8"))}
    except (OSError, URLError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": str(exc)}


def ragd_health() -> dict:
    return http_json(f"{RAGD}/health")


def tmux_sessions() -> str:
    return run(["tmux", "ls"], timeout=3)[1] or "No tmux sessions."


def research_counts() -> dict[str, int | str]:
    path = ROOT / "research" / "research.db"
    if not path.exists():
        return {"status": "missing"}
    try:
        conn = sqlite3.connect(path)
        return {
            "sources": conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0],
            "jobs": conn.execute("SELECT COUNT(*) FROM crawl_jobs").fetchone()[0],
            "documents": conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0],
            "chunks": conn.execute("SELECT COUNT(*) FROM document_chunks").fetchone()[0],
        }
    except Exception as exc:
        return {"status": f"error: {exc}"}


def codex_config_status() -> dict[str, bool]:
    paths = [Path.home() / ".codex" / "config.toml", ROOT / ".codex" / "config.toml"]
    return {str(path): (path.exists() and "ragd" in path.read_text(encoding="utf-8", errors="replace")) for path in paths}


def print_json(data: dict) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def native_binary(name: str) -> Path:
    return ROOT / "ragd" / "build" / name


def run_native_json(cmd: list[str], timeout: int = 60) -> tuple[int, dict]:
    code, output = run(cmd, timeout=timeout)
    try:
        payload = json.loads(output) if output else {}
    except json.JSONDecodeError:
        payload = {"native_fallback": True, "error": output}
    return code, payload


def cmd_native(args: argparse.Namespace) -> int:
    command = args.native_command
    binary_map = {
        "scan": "dominion-native-scan",
        "doctor": "dominion-native-doctor",
        "manifest": "dominion-native-manifest",
        "vault-doctor": "dominion-native-vault-doctor",
        "bench": "dominion-native",
    }
    binary = native_binary(binary_map[command])
    if not binary.exists():
        payload = {"native_fallback": True, "status": "error", "error": f"native binary missing: {binary}"}
        if getattr(args, "json", False):
            print_json(payload)
        else:
            print(payload["error"])
        return 1

    cmd = [str(binary)]
    if command == "bench":
        cmd.append("bench")
    elif command == "manifest":
        cmd.append(args.manifest_command)
    if command in {"scan", "doctor", "vault-doctor", "bench"}:
        cmd.extend(["--root", str(args.root or ROOT)])
    if command == "doctor":
        cmd.append("--offline" if args.offline else "--live" if args.live else "--offline")
        if args.strict:
            cmd.append("--strict")
    if command == "manifest":
        cmd.extend(["--db", str(args.db)])
        if args.manifest_command == "scan":
            cmd.extend(["--root", str(args.root or ROOT)])
    if command == "scan":
        if args.include_ignored:
            cmd.append("--include-ignored")
        if args.strict:
            cmd.append("--strict")
        if args.max_files:
            cmd.extend(["--max-files", str(args.max_files)])
        if args.max_bytes:
            cmd.extend(["--max-bytes", str(args.max_bytes)])
    if command == "vault-doctor" and args.vault:
        cmd.extend(["--vault", str(args.vault)])
    if getattr(args, "json", False) and command not in {"manifest", "vault-doctor", "bench"}:
        cmd.append("--json")

    code, output = run(cmd, timeout=120)
    print(output)
    return code


def cmd_status(args: argparse.Namespace) -> int:
    tailscale = run(["tailscale", "ip", "-4"], timeout=3)[1]
    ssh = run(["service", "ssh", "status"], timeout=3)[1]
    ragd = ragd_health()
    domdata_notice = run(["domdata", "notice"], timeout=20)[1]
    data = {
        "tailscale_ip": tailscale,
        "ssh_active": "Active: active" in ssh,
        "tmux": tmux_sessions(),
        "ragd": ragd,
        "codex_mcp_config": codex_config_status(),
        "domdata_read_only": "READ-ONLY" in domdata_notice and "Blocked forever" in domdata_notice,
        "research": research_counts(),
        "rag_infra": {
            "embed_cache": run([sys.executable, "-m", "ragd_embed.cli", "stats", "--json"], timeout=5)[1],
            "vault": run([sys.executable, "-m", "ragd_vault.cli", "status", "--json"], timeout=5)[1],
        },
    }
    if args.json:
        print_json(data)
    else:
        print("Dominion Status")
        print(f"Tailscale IP: {data['tailscale_ip'] or 'unavailable'}")
        print(f"SSH active: {data['ssh_active']}")
        print("tmux:")
        print(data["tmux"])
        health = ragd.get("data", {}) if ragd.get("ok") else {}
        print(f"RAGD: {health.get('status', 'unreachable')} active_chunks={health.get('active_chunks', 'n/a')} chunks={health.get('chunks', 'n/a')} todos={health.get('todos', 'n/a')} embed_backend={health.get('embed_backend', 'n/a')}")
        print(f"Codex RAGD MCP config: {any(data['codex_mcp_config'].values())}")
        print(f"domdata read-only: {data['domdata_read_only']}")
        print(f"Research: {data['research']}")
        print("RAG infra: see dominion embed stats and dominion vault status")
    return 0 if ragd.get("ok") else 1


def _ragd_start_in_tmux() -> dict:
    """Start RAGD in a tmux session and wait up to 8s for health.
    Returns a dict with ok, method, and message fields.
    """
    import time
    ragd_bin = ROOT / "ragd" / "build" / "ragd"
    if not ragd_bin.exists():
        return {"ok": False, "method": "none", "message": f"ragd binary missing: {ragd_bin}. Run: cmake --build ragd/build -j$(nproc)"}

    # Check if already running
    if ragd_health().get("ok"):
        return {"ok": True, "method": "already_running", "message": "RAGD already healthy"}

    tmux_ok = run(["tmux", "info"], timeout=2)[0] == 0
    ragd_db = Path.home() / ".ragd" / "ragd.db"
    ragd_db.parent.mkdir(parents=True, exist_ok=True)
    ragd_cmd = f"./build/ragd --db {ragd_db} --host 127.0.0.1 --port 7474 --path {ROOT}"

    if tmux_ok:
        run(["tmux", "new-session", "-d", "-s", "ragd", f"cd {ROOT / 'ragd'}; {ragd_cmd} 2>&1 | tee /tmp/ragd.log"], timeout=5)
        method = "tmux"
    else:
        # No tmux — print fallback command and return
        return {
            "ok": False,
            "method": "tmux_unavailable",
            "message": f"tmux not available. Start RAGD manually:\n  cd {ROOT / 'ragd'} && {ragd_cmd}",
        }

    # Poll for up to 8 seconds
    for _ in range(16):
        time.sleep(0.5)
        if ragd_health().get("ok"):
            return {"ok": True, "method": method, "message": "RAGD started and healthy"}

    # Not healthy after wait — get last log lines
    log_tail = run(["tail", "-5", "/tmp/ragd.log"], timeout=2)[1]
    return {
        "ok": False,
        "method": method,
        "message": f"RAGD started but health endpoint not responding after 8s. Last log:\n{log_tail}",
    }


def _ragd_diagnose() -> dict:
    """Return a structured diagnosis for why RAGD might be unreachable."""
    import socket
    ragd_bin = ROOT / "ragd" / "build" / "ragd"
    result: dict = {}

    result["binary_exists"] = ragd_bin.exists()
    if not result["binary_exists"]:
        result["diagnosis"] = "binary_missing"
        result["action"] = "cmake --build ragd/build -j$(nproc)"
        return result

    # Check port
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        connected = s.connect_ex(("127.0.0.1", 7474)) == 0
        s.close()
    except OSError:
        connected = False

    result["port_open"] = connected
    if not connected:
        result["diagnosis"] = "process_not_running"
        result["action"] = "python scripts/dominion_cli.py start"
        return result

    # Port open but health fails
    health = ragd_health()
    result["health_ok"] = health.get("ok", False)
    if not result["health_ok"]:
        result["diagnosis"] = "health_endpoint_unhealthy"
        result["error"] = health.get("error", "unknown")
        result["action"] = "check /tmp/ragd.log or restart ragd session"
        return result

    result["diagnosis"] = "healthy"
    result["data"] = health.get("data", {})
    return result


def cmd_start(args: argparse.Namespace) -> int:
    result: dict = {"services": {}}

    # SSH
    run(["service", "ssh", "start"], timeout=10)

    # tmux sessions
    tmux_ok = run(["tmux", "info"], timeout=2)[0] == 0
    if tmux_ok:
        for name, command in {
            "matin": f"cd {ROOT}; export DOMINION_PERSON=matin; exec bash -l",
            "dan": f"cd {ROOT}; export DOMINION_PERSON=dan; exec bash -l",
            "dominion": f"cd {ROOT}; export DOMINION_PERSON=dominion; exec bash -l",
        }.items():
            if run(["tmux", "has-session", "-t", name], timeout=2)[0] != 0:
                run(["tmux", "new-session", "-d", "-s", name, command], timeout=5)
        for name, cmd in {
            "ragd-chunker": f"cd {ROOT}; exec {sys.executable} -m ragd_chunker.service",
            "ragd-semantic": f"cd {ROOT}; exec {sys.executable} -m ragd_hnsw.semantic_server",
        }.items():
            if run(["tmux", "has-session", "-t", name], timeout=2)[0] != 0:
                run(["tmux", "new-session", "-d", "-s", name, cmd], timeout=5)

    # RAGD
    ragd_result = _ragd_start_in_tmux()
    result["services"]["ragd"] = ragd_result

    overall_ok = ragd_result["ok"]

    if getattr(args, "json", False):
        result["overall"] = "ok" if overall_ok else "warn"
        print_json(result)
    else:
        print("Dominion start")
        ragd_status = "OK" if ragd_result["ok"] else "WARN"
        print(f"  RAGD: [{ragd_status}] {ragd_result['message']}")
        if not ragd_result["ok"]:
            diag = _ragd_diagnose()
            print(f"  RAGD diagnosis: {diag.get('diagnosis', 'unknown')}")
            if diag.get("action"):
                print(f"  Action: {diag['action']}")
        print()
        print("Next commands:")
        print("  python scripts/dominion_cli.py status --json")
        print("  python scripts/dominion_cli.py truth --live --json")
    return 0 if overall_ok else 1


def cmd_doctor(args: argparse.Namespace) -> int:
    strict = getattr(args, "strict", False)
    if getattr(args, "deep", False):
        from dominion_loader.truth_doctor import run_deep_doctor

        report = run_deep_doctor(offline=getattr(args, "offline", False), max_sample=getattr(args, "max_sample", 200))
        if args.json:
            print_json(report)
        else:
            print(f"Dominion deep doctor: {report['overall']}")
            for name, result in report["checks"].items():
                status = result.get("status", "?").upper()
                print(f"  {status} {name}: {result.get('detail', '')}")
        if report["overall"] == "fail":
            return 1
        if strict and report["overall"] == "warn":
            return 1
        return 0

    native_doctor: dict | None = None
    native_doctor_code: int | None = None
    native_doctor_bin = native_binary("dominion-native-doctor")
    if native_doctor_bin.exists() and getattr(args, "offline", False):
        native_cmd = [str(native_doctor_bin), "--root", str(ROOT), "--offline", "--json"]
        native_doctor_code, native_doctor = run_native_json(native_cmd, timeout=90)

    # Foundation checks — always run, no external dependencies
    foundation_checks: dict[str, dict] = {}

    try:
        from dominion_loader.ignore import Ignore
        ig = Ignore()
        rules = ig.builtin_rules()
        secrets_blocked = "secrets" in rules.get("dir_deny", set())
        foundation_checks["ignore_rules"] = {"status": "ok" if secrets_blocked else "warn", "secrets_blocked": secrets_blocked}
    except Exception as exc:
        foundation_checks["ignore_rules"] = {"status": "error", "error": str(exc)}

    try:
        import tempfile
        from dominion_loader.manifest import Manifest
        with tempfile.TemporaryDirectory() as td:
            m = Manifest(Path(td) / "test.db")
            m.stats()
            m.close()
        foundation_checks["manifest"] = {"status": "ok"}
    except Exception as exc:
        foundation_checks["manifest"] = {"status": "error", "error": str(exc)}

    try:
        import tempfile
        from dominion_loader.cache import Cache
        with tempfile.TemporaryDirectory() as td:
            c = Cache(Path(td) / "cache")
            c.put("test", "k", b"v", fingerprint="fp")
            hit = c.get("test", "k", fingerprint="fp")
            assert hit is not None
        foundation_checks["cache"] = {"status": "ok"}
    except Exception as exc:
        foundation_checks["cache"] = {"status": "error", "error": str(exc)}

    try:
        from dominion_loader.ragd_bridge import RagdBridge
        bridge = RagdBridge()
        h = bridge.health()
        foundation_checks["ragd_bridge"] = {"status": "ok", "reachable": h.get("ok", False)}
    except Exception as exc:
        foundation_checks["ragd_bridge"] = {"status": "error", "error": str(exc)}

    try:
        from dominion_loader.profiler import Profiler
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            p = Profiler(Path(td) / "test.db")
            p.close()
        foundation_checks["profiler"] = {"status": "ok"}
    except Exception as exc:
        foundation_checks["profiler"] = {"status": "error", "error": str(exc)}

    try:
        from dominion_loader.semantic_diff import semantic_diff
        result = semantic_diff(b"x = 1\n", b"x = 1\n")
        foundation_checks["semantic_diff"] = {"status": "ok", "test_result": result}
    except Exception as exc:
        foundation_checks["semantic_diff"] = {"status": "error", "error": str(exc)}

    try:
        from dominion_loader.ledger import Ledger
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            l = Ledger(Path(td) / "ledger.db")
            l.stats()
            l.close()
        foundation_checks["ledger_schema"] = {"status": "ok"}
    except Exception as exc:
        foundation_checks["ledger_schema"] = {"status": "error", "error": str(exc)}

    try:
        from ragd_embed.config import load_config
        from ragd_embed.cache import EmbeddingCache
        cfg = load_config(require_key=False)
        foundation_checks["ragd_embed"] = {"status": "ok" if cfg.api_key else "warn", "provider": cfg.provider, "model": cfg.model, "api_key_present": bool(cfg.api_key), "cache": EmbeddingCache(cfg.cache_path).stats()}
    except Exception as exc:
        foundation_checks["ragd_embed"] = {"status": "error", "error": str(exc)}

    try:
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:7475/health", timeout=1) as response:
            chunker_ok = response.status == 200
        foundation_checks["ragd_chunker"] = {"status": "ok" if chunker_ok else "warn", "reachable": chunker_ok}
    except Exception as exc:
        foundation_checks["ragd_chunker"] = {"status": "warn", "reachable": False, "error": str(exc)}

    try:
        from ragd_embed.config import load_config
        from ragd_hnsw.config import default_index_path
        cfg = load_config(require_key=False)
        index_path = default_index_path(cfg.provider, cfg.model, cfg.dim)
        foundation_checks["ragd_hnsw"] = {"status": "ok" if index_path.exists() else "warn", "path": str(index_path), "exists": index_path.exists()}
    except Exception as exc:
        foundation_checks["ragd_hnsw"] = {"status": "error", "error": str(exc)}

    try:
        from ragd_graph.graph import stats as graph_stats
        gs = graph_stats()
        foundation_checks["ragd_graph"] = {"status": "ok" if gs.nodes else "warn", "nodes": gs.nodes, "edges": gs.edges, "by_relation": gs.by_relation}
    except Exception as exc:
        foundation_checks["ragd_graph"] = {"status": "error", "error": str(exc)}

    try:
        from ragd_vault.doctor import inspect_vault
        vr = inspect_vault(ROOT / "vault")
        foundation_checks["ragd_vault"] = {"status": "ok" if vr.ok and vr.total_notes else "warn", "notes": vr.total_notes, "broken_links": len(vr.broken_links), "invalid_frontmatter": len(vr.invalid_frontmatter)}
    except Exception as exc:
        foundation_checks["ragd_vault"] = {"status": "error", "error": str(exc)}

    # Existing platform checks (best-effort, skipped in offline mode)
    offline = getattr(args, "offline", False)
    platform_checks: dict[str, object] = {}
    if offline:
        platform_checks = {
            "ragd_reachable": "skipped (offline)",
            "dominion_health": "skipped (offline)",
            "domdata_notice": "skipped (offline)",
        }
    else:
        platform_checks = {
            "ragd_reachable": ragd_health().get("ok", False),
            "dominion_health": run(["dominion-health"], timeout=30)[0] == 0,
            "domdata_notice": run(["domdata", "notice"], timeout=30)[0] == 0,
        }

    # Optional AI checks (may not exist in Phase 1)
    ai_checks: dict[str, object] = {}
    try:
        from dominion_ai.cli import latest_decisions_panel, latest_queries_panel
        ai_checks["a2_trace_presence"] = bool(latest_queries_panel(1) != "no query traces")
        ai_checks["a2_ledger"] = bool(latest_decisions_panel(1) != "no decisions")
    except ImportError:
        ai_checks["a2_retrieval"] = "unavailable (dominion_ai not installed)"
    except Exception as exc:
        ai_checks["a2_error"] = str(exc)

    all_checks = {**foundation_checks, **platform_checks, **ai_checks}
    if native_doctor is not None:
        foundation_checks["native_doctor"] = {
            "status": "ok" if native_doctor_code == 0 else "error",
            "overall": native_doctor.get("overall"),
            "native_core_version": native_doctor.get("native_core_version"),
        }
        all_checks["native_doctor"] = foundation_checks["native_doctor"]

    def _check_status(v: object) -> str:
        if isinstance(v, dict) and "status" in v:
            return str(v["status"])
        return "ok" if bool(v) else "fail"

    # In offline mode, compute overall only from foundation checks
    # to avoid failing when external services (RAGD, domdata) are unreachable
    checks_for_overall = foundation_checks if offline else all_checks
    check_statuses = [_check_status(v) for v in checks_for_overall.values()]
    if "fail" in check_statuses or "error" in check_statuses:
        overall_str = "fail"
    elif "warn" in check_statuses:
        overall_str = "warn"
    else:
        overall_str = "ok"
    if args.json:
        payload = {"overall": overall_str, "checks": all_checks}
        if native_doctor is not None:
            payload["native_doctor"] = native_doctor
        else:
            payload["native_fallback"] = True
        print_json(payload)
    else:
        print("=== Foundation Checks ===")
        for name, result in foundation_checks.items():
            status = result.get("status", "?") if isinstance(result, dict) else "ok"
            mark = "PASS" if status == "ok" else "WARN" if status == "warn" else "FAIL"
            print(f"  {mark} {name}")
            if args.verbose and isinstance(result, dict) and result.get("error"):
                print(f"       {result['error']}")
        print("=== Platform Checks ===")
        for name, result in platform_checks.items():
            mark = "SKIP" if isinstance(result, str) and result.startswith("skipped") else "PASS" if result else "FAIL"
            print(f"  {mark} {name}")
        if native_doctor is not None:
            print("=== Native Checks ===")
            print(f"  {'PASS' if native_doctor_code == 0 else 'FAIL'} native_doctor overall={native_doctor.get('overall', 'unknown')}")
    if overall_str == "fail":
        return 1
    if strict and overall_str == "warn":
        return 1
    return 0


def cmd_tmux(args: argparse.Namespace) -> int:
    print(tmux_sessions())
    print("Use: warp matin | warp dan | warp dominion | warp codex | warp ragd")
    return 0


def cmd_codex(args: argparse.Namespace) -> int:
    tools = http_json(f"{RAGD}/mcp", {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
    print("Codex")
    print(f"version: {run(['codex', '--version'], timeout=5)[1]}")
    print(f"binary: {shutil.which('codex')}")
    print(f"RAGD MCP config: {codex_config_status()}")
    print(f"RAGD MCP tools reachable: {tools.get('ok', False)}")
    print("Suggested: warp codex")
    return 0 if tools.get("ok") else 1


def cmd_ragd(args: argparse.Namespace) -> int:
    print_json({"health": ragd_health(), "tools": http_json(f"{RAGD}/mcp", {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})})
    return 0


def cmd_research(args: argparse.Namespace) -> int:
    print(run(["research", "status"], timeout=10)[1])
    print(run(["research", "doctor"], timeout=10)[1])
    return 0


def cmd_data(args: argparse.Namespace) -> int:
    for cmd in (["domdata", "notice"], ["domdata", "collect-status"], ["domdata", "xautick"]):
        print(f"$ {' '.join(cmd)}")
        print(run(cmd, timeout=30)[1])
    return 0


def cmd_ignore(args: argparse.Namespace) -> int:
    from dominion_loader.ignore import export_policy, policy_hash

    payload = {"policy_hash": policy_hash(), "policy": export_policy()}
    if args.json:
        print_json(payload)
    else:
        print(f"policy_hash: {payload['policy_hash']}")
        print(f"secrets_always_ignored: {payload['policy']['secrets_always_ignored']}")
    return 0


def cmd_ai_search(args: argparse.Namespace) -> int:
    from dominion_ai.cli import cmd_search

    return cmd_search(args)


def cmd_ai_ask(args: argparse.Namespace) -> int:
    from dominion_ai.cli import cmd_ask

    return cmd_ask(args)


def cmd_ai_explain(args: argparse.Namespace) -> int:
    from dominion_ai.cli import cmd_explain

    return cmd_explain(args)


def cmd_ai_trace(args: argparse.Namespace) -> int:
    from dominion_ai.cli import cmd_trace

    return cmd_trace(args)


def cmd_ai_eval(args: argparse.Namespace) -> int:
    from dominion_ai.cli import cmd_eval

    return cmd_eval(args)


def cmd_ai_ledger(args: argparse.Namespace) -> int:
    from dominion_ai.cli import cmd_ledger

    return cmd_ledger(args)


def cmd_ai_graph(args: argparse.Namespace) -> int:
    from dominion_ai.cli import cmd_graph

    return cmd_graph(args)


def cmd_ai_bench(args: argparse.Namespace) -> int:
    from dominion_ai.cli import cmd_bench

    return cmd_bench(args)


def cmd_embed(args: argparse.Namespace) -> int:
    from ragd_embed.cli import main as embed_main

    argv = [args.embed_command]
    if getattr(args, "changed_only", False):
        argv.append("--changed-only")
    if getattr(args, "json", False):
        argv.append("--json")
    return embed_main(argv)


def cmd_vault(args: argparse.Namespace) -> int:
    from ragd_vault.cli import main as vault_main

    argv = [args.vault_command]
    if getattr(args, "json", False):
        argv.append("--json")
    if args.vault_command == "repair" and getattr(args, "apply", False):
        argv.append("--apply")
    return vault_main(argv)


def _latest_report() -> str:
    reports = (ROOT / "reports").glob("dominion-*-latest.md")
    latest = sorted((p.name for p in reports))
    return latest[-1] if latest else ""


def cmd_phase_report(args: argparse.Namespace) -> int:
    code, status = run(["git", "-C", str(ROOT), "status", "--short"], timeout=10)
    data = {
        "phase": args.phase,
        "root": str(ROOT),
        "git_dirty": bool(status.strip()),
        "git_status_short": status,
        "research_doctor": run(["research", "doctor", "--json"], timeout=10)[1],
        "embed_stats": run([sys.executable, "-m", "ragd_embed.cli", "stats", "--json"], timeout=10)[1],
        "vault_status": run([sys.executable, "-m", "ragd_vault.cli", "status", "--json"], timeout=10)[1],
        "ragd_health": ragd_health(),
        "latest_report": _latest_report(),
        "recommended_validation": [
            "python -m pytest -q",
            "python domdata/check_no_trading.py",
            "./scripts/bootstrap_python.sh",
        ],
    }
    if args.json:
        print_json(data)
    else:
        print(f"Dominion phase-report ({args.phase})")
        print(f"root: {ROOT}")
        print(f"git dirty: {data['git_dirty']}")
        if status.strip():
            print("git status --short:")
            print(status)
        print(f"latest report: {data['latest_report'] or 'none'}")
        print("recommended validation:")
        for cmd in data["recommended_validation"]:
            print(f"  {cmd}")
    return 0


def cmd_next_prompt(args: argparse.Namespace) -> int:
    prompt = "\n".join(
        [
            "You are Codex working in /home/Martin/Dominion.",
            "Follow the Dominion Platform Contract in AGENTS.md (data-only, no secrets, no trading, bounded research).",
            "",
            "Startup protocol:",
            "cd /home/Martin/Dominion",
            "git status --short",
            "cat AGENT_HANDOFF.md",
            "cat PROGRESS.md | tail -n 120",
            "ragd_handoff_read || true",
            "codexrag \"Dominion V2.5\" || true",
            "research ragd-status || true",
            "dominion status || true",
            "",
            "Validation:",
            "python -m pytest -q",
            "python domdata/check_no_trading.py",
            "./scripts/bootstrap_python.sh",
            "",
            f"Current focus: {args.focus}",
        ]
    )
    print(prompt)
    return 0


def cmd_truth(args: argparse.Namespace) -> int:
    """Truth report: doctor --deep + complexity + ignore + RAGD + retrieval infrastructure."""
    import time
    live = getattr(args, "live", False)
    offline = getattr(args, "offline", False) or (not live)
    strict = getattr(args, "strict", False)
    sections: dict = {}

    # 1. Deep doctor (may take a moment)
    try:
        from dominion_loader.truth_doctor import run_deep_doctor
        sections["doctor"] = run_deep_doctor(
            offline=offline,
            max_sample=getattr(args, "max_sample", 200),
        )
    except Exception as exc:
        sections["doctor"] = {"overall": "error", "error": str(exc)}

    # 2. Complexity report
    try:
        from dominion_agent.complexity import all_packages_report
        reports = []
        for r in all_packages_report():
            reports.append({
                "package": r.package,
                "score": r.score,
                "budget": r.budget,
                "over_budget": r.over_budget,
                "warnings": r.warnings,
            })
        sections["complexity"] = {
            "status": "warn" if any(r["over_budget"] for r in reports) else "ok",
            "packages": reports,
        }
    except Exception as exc:
        sections["complexity"] = {"status": "error", "error": str(exc)}

    # 3. Ignore policy
    try:
        from dominion_loader.ignore import Ignore
        ig = Ignore()
        rules = ig.builtin_rules()
        sections["ignore_policy"] = {
            "status": "ok" if "secrets" in rules.get("dir_deny", set()) else "warn",
            "secrets_blocked": "secrets" in rules.get("dir_deny", set()),
            "policy_hash": ig.policy_hash() if hasattr(ig, "policy_hash") else "unavailable",
        }
    except Exception as exc:
        sections["ignore_policy"] = {"status": "error", "error": str(exc)}

    # 4. RAGD metadata + live checks
    ragd = ragd_health()
    ragd_ok = ragd.get("ok", False)
    ragd_section: dict = {
        "status": "ok" if ragd_ok else ("fail" if live else "warn"),
        "reachable": ragd_ok,
        "data": ragd.get("data") or {},
    }
    if live and ragd_ok:
        # Smoke query
        try:
            smoke = http_json(f"{RAGD}/query", {"query": "dominion native manifest", "top_k": 3}, timeout=5)
            smoke_data = smoke.get("data") or {}
            results = smoke_data.get("results", [])
            ragd_section["query_smoke"] = "ok" if smoke.get("ok") and results is not None else "warn"
            ragd_section["query_chunks"] = len(results)
        except Exception as exc:
            ragd_section["query_smoke"] = "warn"
            ragd_section["query_smoke_error"] = str(exc)
    elif live and not ragd_ok:
        diag = _ragd_diagnose()
        ragd_section["diagnosis"] = diag.get("diagnosis", "unknown")
        ragd_section["action"] = diag.get("action", "")
    sections["ragd"] = ragd_section

    # 5. Native doctor (offline or live)
    native_doctor_bin = native_binary("dominion-native-doctor")
    if native_doctor_bin.exists():
        native_mode = "--live" if live else "--offline"
        native_cmd = [str(native_doctor_bin), "--root", str(ROOT), native_mode, "--json"]
        _code, _native = run_native_json(native_cmd, timeout=90)
        native_overall = _native.get("overall", "unknown")
        native_status = "ok" if native_overall in ("ok", "pass") else "warn" if native_overall == "warn" else "fail"
        native_checks = {
            k: v for k, v in (_native.get("checks") or {}).items()
            if isinstance(v, dict) and v.get("status") not in ("ok", "pass", "skip")
        }
        # Known bug: native vault doctor doesn't append .md when resolving wikilinks.
        # Files that exist as <path>.md are falsely reported as missing_target.
        vault_check = native_checks.get("native_vault", {})
        if isinstance(vault_check, dict) and vault_check.get("status") == "warn":
            examples = vault_check.get("details", {}).get("examples", [])
            vault_root_dir = ROOT / "vault"
            false_positives = sum(
                1 for ex in examples
                if (vault_root_dir / (ex.get("link", "") + ".md")).exists()
            )
            if false_positives == len(examples) and examples:
                native_checks["native_vault"] = {
                    "status": "warn",
                    "known_issue": "native doctor .md extension bug - all targets exist",
                    "false_positive_count": false_positives,
                }
        sections["native_doctor"] = {
            "status": native_status,
            "overall": native_overall,
            "checks": native_checks,
        }
    else:
        sections["native_doctor"] = {"status": "warn", "message": "native doctor binary missing"}

    # 6. RAG retrieval infrastructure
    try:
        from ragd_embed.config import load_config
        from ragd_embed.cache import EmbeddingCache
        from ragd_hnsw.config import default_index_path
        from ragd_vault.doctor import inspect_vault
        cfg = load_config(require_key=False)
        index_path = default_index_path(cfg.provider, cfg.model, cfg.dim)
        vault_report = inspect_vault(ROOT / "vault")
        sections["rag_infra"] = {
            "status": "warn" if not cfg.api_key else "ok",
            "embedding_provider": cfg.provider,
            "embedding_model": cfg.model,
            "api_key_present": bool(cfg.api_key),
            "embed_cache": EmbeddingCache().stats(),
            "hnsw_index_exists": index_path.exists(),
            "vault_notes": vault_report.total_notes,
            "vault_broken_links": len(vault_report.broken_links),
        }
    except Exception as exc:
        sections["rag_infra"] = {"status": "warn", "error": str(exc)}

    # Overall
    statuses = [s.get("status", "?") for s in sections.values() if isinstance(s, dict)]
    if "error" in statuses or "fail" in statuses:
        overall = "fail"
    elif "warn" in statuses:
        overall = "warn"
    else:
        overall = "ok"

    result = {
        "overall": overall,
        "mode": "live" if live else "offline",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sections": sections,
    }

    if getattr(args, "json", False):
        print_json(result)
    else:
        print(f"=== Dominion Truth Report [{result['mode'].upper()}]  {result['generated_at']} ===")
        print(f"Overall: {overall.upper()}")
        print()
        for name, sec in sections.items():
            if isinstance(sec, dict):
                status = sec.get("overall") or sec.get("status", "?")
                mark = "PASS" if status in ("ok", "pass") else "SKIP" if status == "skip" else "WARN" if status == "warn" else "FAIL"
                print(f"  {mark}  {name}")
                if name == "complexity":
                    for pkg in sec.get("packages", []):
                        if pkg["over_budget"]:
                            print(f"         OVER  {pkg['package']}  {pkg['score']:.1f}/{pkg['budget']:.1f}")
                elif name == "doctor":
                    for check_name, check_val in sec.get("checks", {}).items():
                        cs = check_val.get("status", "?") if isinstance(check_val, dict) else str(check_val)
                        if cs not in ("ok", "pass"):
                            print(f"         WARN  {check_name}: {cs}")
                elif name in ("ragd", "native_doctor"):
                    for k, v in sec.items():
                        if k not in ("status", "data", "checks") and v not in (True, None, {}):
                            print(f"         {k}: {v}")

    # Exit code: strict mode exits 1 on warn
    if overall == "fail":
        return 1
    if strict and overall == "warn":
        return 1
    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    from dominion_loader.cli import cmd_scan as _cmd
    return _cmd(args)


def cmd_cache(args: argparse.Namespace) -> int:
    from dominion_loader.cli import cmd_cache as _cmd
    return _cmd(args)


def cmd_manifest(args: argparse.Namespace) -> int:
    from dominion_loader.cli import cmd_manifest as _cmd
    return _cmd(args)


def cmd_loader_bench(args: argparse.Namespace) -> int:
    from dominion_loader.cli import cmd_loader_bench as _cmd
    return _cmd(args)


def cmd_loader_ledger(args: argparse.Namespace) -> int:
    from dominion_loader.cli import cmd_loader_ledger as _cmd
    return _cmd(args)


def cmd_graph_foundation(args: argparse.Namespace) -> int:
    from dominion_loader.cli import cmd_graph_foundation as _cmd
    return _cmd(args)


# Microstructure subsystem commands
def cmd_lob(args: argparse.Namespace) -> int:
    """LOB reconstruction commands."""
    import sys
    sys.argv = ["lob.cli", args.lob_command] + (args.extra or [])
    from lob import cli
    return cli.main()


def cmd_sim(args: argparse.Namespace) -> int:
    """Execution simulator commands."""
    import sys
    sys.argv = ["exec_sim.cli", args.sim_command] + (args.extra or [])
    from exec_sim import cli
    return cli.main()


def cmd_tca(args: argparse.Namespace) -> int:
    """TCA commands."""
    import sys
    sys.argv = ["tca.cli", args.tca_command] + (args.extra or [])
    from tca import cli
    return cli.main()


def cmd_toxicity(args: argparse.Namespace) -> int:
    """Toxicity monitor commands."""
    import sys
    sys.argv = ["toxicity.cli", args.toxicity_command] + (args.extra or [])
    from toxicity import cli
    return cli.main()


def cmd_exec_features(args: argparse.Namespace) -> int:
    """Execution features commands."""
    import sys
    sys.argv = ["exec_features.cli", args.exec_features_command] + (args.extra or [])
    from exec_features import cli
    return cli.main()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dominion", description="Dominion V2 command center")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, func in (
        ("start", cmd_start),
        ("health", cmd_status),
        ("status", cmd_status),
        ("tmux", cmd_tmux),
        ("codex", cmd_codex),
        ("ragd", cmd_ragd),
        ("research", cmd_research),
        ("data", cmd_data),
    ):
        p = sub.add_parser(name)
        p.add_argument("--json", action="store_true") if name in {"status", "health"} else None
        p.set_defaults(func=func)
    p = sub.add_parser("doctor")
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--json", action="store_true")
    p.add_argument("--deep", action="store_true")
    p.add_argument("--offline", action="store_true")
    p.add_argument("--strict", action="store_true", help="Exit 1 on warn as well as fail")
    p.add_argument("--max-sample", type=int, default=200)
    p.set_defaults(func=cmd_doctor)
    p = sub.add_parser("help")
    p.set_defaults(func=lambda args: (parser.print_help() or 0))

    p = sub.add_parser("phase-report")
    p.add_argument("--phase", default="v2.5")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_phase_report)

    p = sub.add_parser("next-prompt")
    p.add_argument("--focus", default="Continue Dominion V2.5 phase work")
    p.set_defaults(func=cmd_next_prompt)

    p = sub.add_parser("truth", help="Full truth report: doctor+complexity+ignore+ragd+retrieval")
    p.add_argument("--json", action="store_true")
    p.add_argument("--offline", action="store_true")
    p.add_argument("--live", action="store_true", help="Require live RAGD; fail if unreachable")
    p.add_argument("--strict", action="store_true", help="Exit 1 on warn as well as fail")
    p.add_argument("--max-sample", type=int, default=200)
    p.set_defaults(func=cmd_truth)

    p = sub.add_parser("search")
    p.add_argument("query")
    p.add_argument("--top-k", type=int, default=10)
    p.add_argument("--mode", choices=["hybrid", "bm25", "vector"], default="hybrid")
    p.add_argument("--rerank", choices=["heuristic", "off"], default="heuristic")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_ai_search)

    p = sub.add_parser("ask")
    p.add_argument("query")
    p.add_argument("--top-k", type=int, default=10)
    p.add_argument("--generate", action="store_true")
    p.add_argument("--retrieve-only", action="store_true")
    p.add_argument("--budget", type=int, default=4096)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_ai_ask)

    p = sub.add_parser("explain")
    p.add_argument("--chunk", required=True)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_ai_explain)

    p = sub.add_parser("trace")
    p.add_argument("trace_id")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_ai_trace)

    p = sub.add_parser("eval")
    p.add_argument("--bundle", required=True)
    p.add_argument("--top-k", type=int, default=10)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_ai_eval)

    p = sub.add_parser("ledger")
    ledger_sub = p.add_subparsers(dest="ledger_command", required=True)
    lp = ledger_sub.add_parser("list")
    lp.add_argument("--kind", default=None)
    lp.add_argument("--session", default=None)
    lp.add_argument("--tag", default=None)
    lp.add_argument("--since", default=None)
    lp.add_argument("--limit", type=int, default=50)
    lp.add_argument("--json", action="store_true")
    lp.set_defaults(func=cmd_ai_ledger)
    lp = ledger_sub.add_parser("show")
    lp.add_argument("entry_id")
    lp.add_argument("--json", action="store_true")
    lp.set_defaults(func=cmd_ai_ledger)
    lp = ledger_sub.add_parser("search")
    lp.add_argument("query")
    lp.add_argument("--limit", type=int, default=20)
    lp.add_argument("--json", action="store_true")
    lp.set_defaults(func=cmd_ai_ledger)

    p = sub.add_parser("embed")
    embed_sub = p.add_subparsers(dest="embed_command", required=True)
    ep = embed_sub.add_parser("run")
    ep.add_argument("--changed-only", action="store_true")
    ep.add_argument("--json", action="store_true")
    ep.set_defaults(func=cmd_embed)
    ep = embed_sub.add_parser("stats")
    ep.add_argument("--json", action="store_true")
    ep.set_defaults(func=cmd_embed)
    ep = embed_sub.add_parser("doctor")
    ep.add_argument("--json", action="store_true")
    ep.set_defaults(func=cmd_embed)

    p = sub.add_parser("vault")
    vault_sub = p.add_subparsers(dest="vault_command", required=True)
    for name in ("build", "sync", "status", "doctor", "open"):
        vp = vault_sub.add_parser(name)
        vp.add_argument("--json", action="store_true") if name in {"status", "doctor"} else None
        vp.set_defaults(func=cmd_vault)
    vp = vault_sub.add_parser("repair")
    vp.add_argument("--dry-run", action="store_true", default=True)
    vp.add_argument("--apply", action="store_true")
    vp.add_argument("--json", action="store_true")
    vp.set_defaults(func=cmd_vault)

    p = sub.add_parser("graph")
    graph_sub = p.add_subparsers(dest="graph_command", required=True)
    gp = graph_sub.add_parser("query")
    gp.add_argument("--from", dest="from_file", default="")
    gp.add_argument("--to", dest="to_file", default="")
    gp.add_argument("--depth", type=int, default=3)
    gp.add_argument("--json", action="store_true")
    gp.set_defaults(func=cmd_ai_graph)
    gp = graph_sub.add_parser("neighbors")
    gp.add_argument("--node", default="")
    gp.add_argument("--depth", type=int, default=3)
    gp.add_argument("--json", action="store_true")
    gp.set_defaults(func=cmd_ai_graph)
    gp = graph_sub.add_parser("subgraph")
    gp.add_argument("--label", default="")
    gp.add_argument("--depth", type=int, default=3)
    gp.add_argument("--json", action="store_true")
    gp.set_defaults(func=cmd_ai_graph)

    for name in ("build", "stats", "callers", "callees", "imports", "importers"):
        gp = graph_sub.add_parser(name)
        if name in {"callers", "callees"}:
            gp.add_argument("symbol", nargs="?")
        if name in {"imports", "importers"}:
            gp.add_argument("filepath", nargs="?")
        gp.add_argument("--json", action="store_true")
        gp.set_defaults(func=cmd_ai_graph)

    p = sub.add_parser("bench")
    p.add_argument("--suite", choices=["retrieval", "semantic", "hybrid", "e2e"], default="retrieval")
    p.add_argument("--iterations", type=int, default=3)
    p.set_defaults(func=cmd_ai_bench)

    p = sub.add_parser("ignore")
    ignore_sub = p.add_subparsers(dest="ignore_command", required=True)
    ip = ignore_sub.add_parser("policy")
    ip.add_argument("--json", action="store_true")
    ip.set_defaults(func=cmd_ignore)

    p = sub.add_parser("native", help="Dominion native C++ core tools")
    native_sub = p.add_subparsers(dest="native_command", required=True)

    np = native_sub.add_parser("scan")
    np.add_argument("--root", default=None)
    np.add_argument("--json", action="store_true")
    np.add_argument("--include-ignored", action="store_true")
    np.add_argument("--strict", action="store_true")
    np.add_argument("--max-files", type=int, default=0)
    np.add_argument("--max-bytes", type=int, default=0)
    np.set_defaults(func=cmd_native)

    np = native_sub.add_parser("doctor")
    np.add_argument("--root", default=None)
    np.add_argument("--json", action="store_true")
    np.add_argument("--offline", action="store_true")
    np.add_argument("--live", action="store_true")
    np.add_argument("--strict", action="store_true")
    np.set_defaults(func=cmd_native)

    np = native_sub.add_parser("vault-doctor")
    np.add_argument("--root", default=None)
    np.add_argument("--vault", default=None)
    np.add_argument("--json", action="store_true")
    np.set_defaults(func=cmd_native)

    np = native_sub.add_parser("bench")
    np.add_argument("--root", default=None)
    np.add_argument("--json", action="store_true")
    np.set_defaults(func=cmd_native)

    np = native_sub.add_parser("manifest")
    manifest_native_sub = np.add_subparsers(dest="manifest_command", required=True)
    for manifest_command in ("init", "scan", "doctor"):
        mpn = manifest_native_sub.add_parser(manifest_command)
        mpn.add_argument("--db", default=str(Path.home() / ".dominion" / "native_manifest.db"))
        mpn.add_argument("--root", default=None)
        mpn.add_argument("--json", action="store_true")
        mpn.set_defaults(func=cmd_native)

    # -----------------------------------------------------------------------
    # Foundation (Agent 1) subcommands
    # -----------------------------------------------------------------------
    p = sub.add_parser("scan", help="Scan the repo and update the loader manifest")
    p.add_argument("--repo", default=None, help="Repo root path (default: DOMINION_ROOT)")
    p.add_argument("--once", action="store_true", default=True, help="Run once (default)")
    p.add_argument("--dry-run", action="store_true", help="Discover+hash without writing manifest or RAGD")
    p.add_argument("--native", action="store_true", help="Use native C++ binary for file discovery and hashing")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_scan)

    p = sub.add_parser("cache", help="Manage the loader content cache")
    cache_sub = p.add_subparsers(dest="cache_command", required=True)
    cp = cache_sub.add_parser("stats")
    cp.add_argument("--json", action="store_true")
    cp.set_defaults(func=cmd_cache)
    cp = cache_sub.add_parser("verify")
    cp.add_argument("--json", action="store_true")
    cp.set_defaults(func=cmd_cache)
    cp = cache_sub.add_parser("nuke")
    cp.add_argument("--json", action="store_true")
    cp.set_defaults(func=cmd_cache)

    p = sub.add_parser("manifest", help="Inspect the loader manifest")
    manifest_sub = p.add_subparsers(dest="manifest_command", required=True)
    mp = manifest_sub.add_parser("list")
    mp.add_argument("--changed-since", dest="changed_since", default=None, metavar="ISO")
    mp.add_argument("--json", action="store_true")
    mp.set_defaults(func=cmd_manifest)
    mp = manifest_sub.add_parser("stats")
    mp.add_argument("--json", action="store_true")
    mp.set_defaults(func=cmd_manifest)

    p = sub.add_parser("loader-bench", help="Run dominion_loader benchmark suite")
    p.add_argument("--suite", default="foundation", help="Suite name (default: foundation)")
    p.add_argument("--runs", type=int, default=3)
    p.add_argument("--out", default=None, help="Output directory for JSON results")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_loader_bench)

    p = sub.add_parser("loader-ledger", help="Append entries to the multi-agent memory ledger")
    loader_ledger_sub = p.add_subparsers(dest="loader_ledger_command", required=True)
    llp = loader_ledger_sub.add_parser("append")
    llp.add_argument("--kind", required=True, help="Entry kind (decision|assumption|risk|...)")
    llp.add_argument("--payload", default="{}", help="JSON payload string")
    llp.add_argument("--json", action="store_true")
    llp.set_defaults(func=cmd_loader_ledger)
    llp = loader_ledger_sub.add_parser("stats")
    llp.add_argument("--json", action="store_true")
    llp.set_defaults(func=cmd_loader_ledger)

    p = sub.add_parser("gstats", help="Foundation knowledge graph stats/build")
    gf_sub = p.add_subparsers(dest="graph_foundation_command", required=True)
    gfp = gf_sub.add_parser("stats")
    gfp.add_argument("--json", action="store_true")
    gfp.set_defaults(func=cmd_graph_foundation)
    gfp = gf_sub.add_parser("build")
    gfp.add_argument("--json", action="store_true")
    gfp.set_defaults(func=cmd_graph_foundation)

    # -----------------------------------------------------------------------
    # Agent OS (Agent 4) subcommands
    # -----------------------------------------------------------------------
    try:
        from dominion_agent.cli import build_agent_subparser, cmd_agent
        build_agent_subparser(sub)
    except ImportError:
        pass  # dominion_agent not yet installed

    # -----------------------------------------------------------------------
    # Microstructure subsystems
    # -----------------------------------------------------------------------
    p = sub.add_parser("lob", help="LOB reconstruction engine")
    p.add_argument("lob_command", choices=["compute", "metrics", "vpin"])
    p.add_argument("extra", nargs="*")
    p.set_defaults(func=cmd_lob)

    p = sub.add_parser("sim", help="Execution simulator")
    p.add_argument("sim_command", choices=["run", "report", "compare"])
    p.add_argument("extra", nargs="*")
    p.set_defaults(func=cmd_sim)

    p = sub.add_parser("tca", help="Trade cost analysis")
    p.add_argument("tca_command", choices=["analyze", "report", "heatmap"])
    p.add_argument("extra", nargs="*")
    p.set_defaults(func=cmd_tca)

    p = sub.add_parser("toxicity", help="Order flow toxicity monitor")
    p.add_argument("toxicity_command", choices=["compute", "status", "alerts"])
    p.add_argument("extra", nargs="*")
    p.set_defaults(func=cmd_toxicity)

    p = sub.add_parser("exec-features", help="Execution alpha features")
    p.add_argument("exec_features_command", choices=["compute", "top", "decay"])
    p.add_argument("extra", nargs="*")
    p.set_defaults(func=cmd_exec_features)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
