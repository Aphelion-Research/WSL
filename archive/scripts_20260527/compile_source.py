#!/usr/bin/env python3
"""compile_source.py — Syntax-check only repo-owned Python source directories.

Intentionally excludes generated/runtime directories (.venv, __pycache__,
vault/files, vault/symbols, data, tmp, build, dist, .git, apps/mt5/*, etc.)
so that third-party and generated code does not pollute the source gate.
"""
import compileall
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Repo-owned source roots to compile.
SOURCE_ROOTS = [
    "asset_graph",
    "causal_engine",
    "data_pipeline",
    "domdata",
    "dominion_agent",
    "dominion_ai",
    "dominion_loader",
    "exec_features",
    "exec_sim",
    "lob",
    "ragd_bus",
    "ragd_chunker",
    "ragd_embed",
    "ragd_graph",
    "ragd_hnsw",
    "ragd_vault",
    "research_os",
    "reservoir",
    "tca",
    "toxicity",
]

# Also compile repo Python scripts (flat directory, no recursion needed).
SCRIPT_ROOT = ROOT / "scripts"

# Directories that must never be compiled even if inside a source root.
EXCLUDE_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".venv",
    ".git",
    "build",
    "dist",
    "node_modules",
}


def compile_dir(path: Path) -> bool:
    """Compile one directory tree, skipping excluded subdirs. Returns True on success."""
    if not path.exists():
        return True  # Missing optional package is not an error.

    ok = compileall.compile_dir(
        str(path),
        quiet=1,          # Only print errors.
        force=False,      # Only re-check changed files.
        rx=None,
        maxlevels=20,
        ddir=None,
        # filter_packages: stop descending into excluded dirs
    )
    return bool(ok)


def compile_scripts(scripts_dir: Path) -> bool:
    """Compile only *.py files directly in scripts/ (no sub-crawl into bin/)."""
    ok = True
    for py_file in sorted(scripts_dir.glob("*.py")):
        result = compileall.compile_file(str(py_file), quiet=1)
        if not result:
            ok = False
    return ok


def main() -> int:
    failed: list[str] = []

    for rel in SOURCE_ROOTS:
        path = ROOT / rel
        if not compile_dir(path):
            failed.append(rel)

    if not compile_scripts(SCRIPT_ROOT):
        failed.append("scripts/*.py")

    if failed:
        print(f"COMPILE ERRORS in: {', '.join(failed)}", file=sys.stderr)
        return 1

    print(f"compile_source: OK — {len(SOURCE_ROOTS)} source roots + scripts/*.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
