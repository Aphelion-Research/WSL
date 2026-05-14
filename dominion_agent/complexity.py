"""Complexity budget tracker for Dominion Agent OS.

Scans Python packages and assigns a complexity score.
Warns when a package exceeds its budget.
"""
from __future__ import annotations

import ast
import os
import re
from pathlib import Path
from typing import Optional

from dominion_agent.types import ComplexityMetrics, ComplexityReport


# ---------------------------------------------------------------------------
# Budgets: max score per package (lower = stricter)
# ---------------------------------------------------------------------------
COMPLEXITY_BUDGETS: dict[str, float] = {
    "dominion_loader": 50.0,      # target: well under (score ~0 with good test coverage)
    "dominion_ai": 130.0,         # target: reduce to 100 (currently ~105)
    "dominion_agent": 350.0,      # large CLI package (59 cmds); target reduction in Phase 6
    "ragd_embed": 75.0,           # external embedding pipeline
    "ragd_hnsw": 75.0,            # persistent semantic index
    "ragd_chunker": 90.0,         # AST chunking service
    "ragd_graph": 75.0,           # symbol/import/call graph
    "ragd_vault": 100.0,          # Obsidian vault generation
    "ragd": 80.0,                 # C++ core; Python wrappers only (currently ~44)
    "domdata": 155.0,             # target: reduce to 100 (currently ~138)
    "research_os": 175.0,         # target: reduce to 120 (currently ~157)
    "scripts": 200.0,             # single-file CLI dispatcher; target to split (currently ~192)
    "tests": 20.0,                # keep strict — test code must stay simple
}
_DEFAULT_BUDGET = 50.0


# ---------------------------------------------------------------------------
# Score formula constants
# ---------------------------------------------------------------------------
_W = {
    "file_count": 1.5,
    "public_symbol_count": 0.3,
    "cli_command_count": 2.0,
    "test_count": -1.0,       # tests REDUCE complexity score
    "todo_count": 2.5,
    "temp_adapter_count": 5.0,
    "broad_except_count": 1.5,
    "untested_module_count": 3.0,
    "large_file_penalty": 1.0,
}


def _walk_py_files(root: Path) -> list[Path]:
    """Walk directory for .py files, skipping __pycache__ and build dirs."""
    result: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip common build/cache dirs
        dirnames[:] = [
            d for d in dirnames
            if d not in {"__pycache__", ".venv", "build", "dist", ".git", "node_modules"}
        ]
        for fn in filenames:
            if fn.endswith(".py"):
                result.append(Path(dirpath) / fn)
    return result


def _count_public_symbols(tree: ast.Module) -> int:
    """Count top-level public functions and classes."""
    count = 0
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not node.name.startswith("_"):
                count += 1
    return count


def _count_broad_excepts(source: str) -> int:
    """Count bare `except:` or `except Exception:` blocks."""
    pattern = re.compile(r"^\s*except\s*(Exception|BaseException|:)", re.MULTILINE)
    return len(pattern.findall(source))


def _count_todos(source: str) -> int:
    pattern = re.compile(r"TODO|FIXME|HACK|XXX", re.IGNORECASE)
    return len(pattern.findall(source))


def _count_temp_adapters(source: str) -> int:
    # Only count actual TEMP_ADAPTER labels: TEMP_ADAPTER(agent-N) or TEMP_ADAPTER(name)
    # Pattern: TEMP_ADAPTER followed by ( and NOT just (s) or similar commentary.
    # Convention: TEMP_ADAPTER(agent-1): ...
    return len(re.findall(r"TEMP_ADAPTER\([a-zA-Z]", source))


def _large_file_penalty(lines: int) -> float:
    """Score penalty for files over 300 lines."""
    if lines <= 300:
        return 0.0
    elif lines <= 600:
        return 1.0
    elif lines <= 1000:
        return 2.0
    else:
        return 4.0


def _scan_package(path: Path) -> ComplexityMetrics:
    """Scan a directory of Python files and return metrics."""
    py_files = _walk_py_files(path)

    if not py_files:
        return ComplexityMetrics(
            file_count=0,
            public_symbol_count=0,
            cli_command_count=0,
            test_count=0,
            todo_count=0,
            temp_adapter_count=0,
            broad_except_count=0,
            untested_module_count=0,
            large_file_penalty=0.0,
            average_file_lines=0.0,
            largest_file_lines=0,
            test_to_source_ratio=0.0,
        )

    file_count = len(py_files)
    public_symbols = 0
    cli_commands = 0
    test_count = 0
    todo_count = 0
    temp_adapter_count = 0
    broad_excepts = 0
    line_counts: list[int] = []
    large_pen = 0.0
    module_names: set[str] = set()
    tested_names: set[str] = set()

    for fp in py_files:
        try:
            source = fp.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        lines = source.count("\n")
        line_counts.append(lines)
        large_pen += _large_file_penalty(lines)

        todo_count += _count_todos(source)
        temp_adapter_count += _count_temp_adapters(source)
        broad_excepts += _count_broad_excepts(source)

        # Count test functions
        if fp.name.startswith("test_") or "/tests/" in str(fp):
            test_matches = re.findall(r"def (test_\w+)", source)
            test_count += len(test_matches)
            # Track which modules are tested
            tested_matches = re.findall(r"from\s+(\S+)\s+import|import\s+(\S+)", source)
            for m in tested_matches:
                name = m[0] or m[1]
                tested_names.add(name.split(".")[0])
        else:
            # Non-test: count public symbols and CLI commands
            try:
                tree = ast.parse(source)
                public_symbols += _count_public_symbols(tree)
                # Count CLI commands (add_argument and add_parser calls)
                cli_commands += source.count("add_argument(")
                cli_commands += source.count("add_parser(")
            except SyntaxError:
                pass
            module_names.add(fp.stem)

        # (add_parser formerly counted outside branch and double-deduplicated; now fixed)

    # Untested modules: modules with no corresponding test
    untested = len(module_names - {"__init__", "__main__"} - tested_names)

    avg_lines = sum(line_counts) / len(line_counts) if line_counts else 0.0
    max_lines = max(line_counts) if line_counts else 0

    # Test-to-source ratio: test_count / max(1, public_symbols)
    test_to_source_ratio = round(test_count / max(1, public_symbols), 2)

    return ComplexityMetrics(
        file_count=file_count,
        public_symbol_count=public_symbols,
        cli_command_count=cli_commands,
        test_count=test_count,
        todo_count=todo_count,
        temp_adapter_count=temp_adapter_count,
        broad_except_count=broad_excepts,
        untested_module_count=untested,
        large_file_penalty=round(large_pen, 2),
        average_file_lines=round(avg_lines, 1),
        largest_file_lines=max_lines,
        test_to_source_ratio=test_to_source_ratio,
    )


def _compute_score(m: ComplexityMetrics) -> float:
    """Compute complexity score from metrics.

    Test count reduces the score (encouraging testing) but is capped so that
    a high test count cannot hide real structural debt (TODOs, broad excepts,
    untested modules, TEMP_ADAPTERs).  Test credit is limited to at most the
    combined file/symbol contribution — it cannot offset penalty terms.
    """
    # Positive (debt) terms
    debt = (
        m.file_count * _W["file_count"]
        + m.public_symbol_count * _W["public_symbol_count"]
        + m.cli_command_count * _W["cli_command_count"]
        + m.todo_count * _W["todo_count"]
        + m.temp_adapter_count * _W["temp_adapter_count"]
        + m.broad_except_count * _W["broad_except_count"]
        + m.untested_module_count * _W["untested_module_count"]
        + m.large_file_penalty * _W["large_file_penalty"]
    )
    # Test credit: can only offset file_count + public_symbol_count contribution
    max_test_credit = (
        m.file_count * _W["file_count"]
        + m.public_symbol_count * _W["public_symbol_count"]
    )
    test_credit = min(m.test_count * abs(_W["test_count"]), max_test_credit)
    return max(0.0, round(debt - test_credit, 2))


def complexity_report(
    package: str,
    root: Optional[str] = None,
) -> ComplexityReport:
    """Compute complexity report for a named package.

    Args:
        package: Package directory name (e.g. 'dominion_loader')
        root: Workspace root directory. Defaults to cwd.
    """
    workspace_root = Path(root) if root else Path.cwd()
    package_path = workspace_root / package

    if not package_path.exists():
        return ComplexityReport(
            package=package,
            score=0.0,
            budget=COMPLEXITY_BUDGETS.get(package, _DEFAULT_BUDGET),
            over_budget=False,
            metrics=ComplexityMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0.0, 0, 0.0),
            warnings=[f"Package directory not found: {package_path}"],
            remediation=[],
        )

    metrics = _scan_package(package_path)
    score = _compute_score(metrics)
    budget = COMPLEXITY_BUDGETS.get(package, _DEFAULT_BUDGET)
    over_budget = score > budget

    warnings: list[str] = []
    remediation: list[str] = []

    if over_budget:
        warnings.append(f"Score {score} exceeds budget {budget}")
        remediation.append(f"dominion agent complexity budget --package {package}")

    if metrics.temp_adapter_count > 0:
        warnings.append(f"{metrics.temp_adapter_count} TEMP_ADAPTER(s) found — schedule removal")
        remediation.append("Search for TEMP_ADAPTER comments and resolve them")

    if metrics.todo_count > 5:
        warnings.append(f"{metrics.todo_count} TODO/FIXME markers — technical debt accumulating")
        remediation.append("Address or assign TODO items before adding new features")

    if metrics.broad_except_count > 3:
        warnings.append(f"{metrics.broad_except_count} broad exception handlers — hides errors")
        remediation.append("Replace broad `except Exception:` with specific exception types")

    if metrics.untested_module_count > 3:
        warnings.append(f"{metrics.untested_module_count} untested modules")
        remediation.append(f"Add tests for untested modules in {package}/tests/")

    if metrics.largest_file_lines > 500:
        warnings.append(f"Largest file has {metrics.largest_file_lines} lines — consider splitting")
        remediation.append("Split large files into focused, single-responsibility modules")

    return ComplexityReport(
        package=package,
        score=score,
        budget=budget,
        over_budget=over_budget,
        metrics=metrics,
        warnings=warnings,
        remediation=remediation,
    )


def all_packages_report(root: Optional[str] = None) -> list[ComplexityReport]:
    """Run complexity report for all budgeted packages."""
    return [complexity_report(pkg, root=root) for pkg in COMPLEXITY_BUDGETS]
