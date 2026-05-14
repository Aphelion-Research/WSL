"""Causal impact analyzer for Dominion Agent OS.

Maps changed files to required validation commands.
Rules-based first; RAGD optional context layer.
"""
from __future__ import annotations

import json
from typing import Optional

from dominion_agent.store import AgentStore
from dominion_agent.types import ImpactReport


# ---------------------------------------------------------------------------
# Package-to-command mapping
# ---------------------------------------------------------------------------

class _Rule:
    __slots__ = ("prefix", "package", "risk", "required", "optional", "tests")

    def __init__(self, prefix: str, package: str, risk: str,
                 required: list[str], optional: list[str], tests: list[str]) -> None:
        self.prefix = prefix
        self.package = package
        self.risk = risk
        self.required = required
        self.optional = optional
        self.tests = tests


_RULES: list[_Rule] = [
    _Rule(
        prefix="dominion_loader/",
        package="dominion_loader",
        risk="medium",
        required=["python -m pytest -q dominion_loader/tests"],
        optional=["dominion doctor --deep --json || true"],
        tests=["dominion_loader/tests/test_scan.py",
               "dominion_loader/tests/test_manifest.py"],
    ),
    _Rule(
        prefix="dominion_ai/",
        package="dominion_ai",
        risk="medium",
        required=["python -m pytest -q dominion_ai/tests"],
        optional=[
            "dominion ask \"how does the handoff protocol work\" --json || true",
            "dominion eval --bundle dominion_ai/tests/eval_fixtures/tiny --top-k 10 --json || true",
        ],
        tests=["dominion_ai/tests/"],
    ),
    _Rule(
        prefix="dominion_agent/",
        package="dominion_agent",
        risk="medium",
        required=["python -m pytest -q dominion_agent/tests"],
        optional=["dominion agent complexity report --json || true"],
        tests=["dominion_agent/tests/"],
    ),
    _Rule(
        prefix="local_llm/",
        package="local_llm",
        risk="medium",
        required=["python -m pytest -q local_llm/tests"],
        optional=["llm doctor --json || true"],
        tests=["local_llm/tests/"],
    ),
    _Rule(
        prefix="ragd/",
        package="ragd",
        risk="high",
        required=[
            "cmake -S ragd -B ragd/build -DCMAKE_BUILD_TYPE=RelWithDebInfo",
            "cmake --build ragd/build -j$(nproc)",
            "ctest --test-dir ragd/build --output-on-failure",
        ],
        optional=["dominion ragd || true"],
        tests=["ragd/tests/"],
    ),
    _Rule(
        prefix="domdata/",
        package="domdata",
        risk="critical",
        required=[
            "python domdata/check_no_trading.py",
            "domdata notice",
            "domdata order-send || true",
        ],
        optional=[],
        tests=["domdata/tests/"],
    ),
    _Rule(
        prefix="research_os/",
        package="research_os",
        risk="low",
        required=["python -m pytest -q research_os/tests"],
        optional=["research status || true"],
        tests=["research_os/tests/"],
    ),
    _Rule(
        prefix="scripts/dominion_cli.py",
        package="scripts",
        risk="medium",
        required=["python -m pytest -q"],
        optional=[
            "dominion status || true",
            "dominion doctor --json || true",
            "dominion-ui --once || true",
        ],
        tests=[],
    ),
    _Rule(
        prefix="scripts/dominion_ui.py",
        package="scripts",
        risk="low",
        required=["dominion-ui --once || true"],
        optional=[],
        tests=[],
    ),
    _Rule(
        prefix="docs/",
        package="docs",
        risk="low",
        required=[],
        optional=["dominion agent architecture refresh --json || true"],
        tests=[],
    ),
    _Rule(
        prefix="pytest.ini",
        package="scripts",
        risk="high",
        required=["python -m pytest -q"],
        optional=[],
        tests=[],
    ),
]

# Default catch-all when no specific rule matches
_DEFAULT_RULE = _Rule(
    prefix="",
    package="unknown",
    risk="medium",
    required=["python -m pytest -q"],
    optional=["dominion doctor --json || true"],
    tests=[],
)


def _match_rules(filepath: str) -> list[_Rule]:
    """Return all rules whose prefix matches the filepath."""
    matched: list[_Rule] = []
    for rule in _RULES:
        if filepath.startswith(rule.prefix) or rule.prefix in filepath:
            matched.append(rule)
    return matched or [_DEFAULT_RULE]


def analyze_impact(
    files: Optional[list[str]] = None,
    task_id: Optional[str] = None,
    *,
    store: Optional[AgentStore] = None,
) -> ImpactReport:
    """Given changed files, predict what must be tested and what may break.

    If task_id provided, reads scope from task.
    """
    target_files: list[str] = list(files or [])

    if task_id and store is not None:
        row = store.conn.execute(
            "SELECT scope_json FROM agent_tasks WHERE task_id=?", (task_id,)
        ).fetchone()
        if row:
            try:
                scope = json.loads(row["scope_json"] or "{}")
                target_files.extend(scope.get("files", []))
            except Exception:
                pass
    elif task_id:
        _store = AgentStore()
        row = _store.conn.execute(
            "SELECT scope_json FROM agent_tasks WHERE task_id=?", (task_id,)
        ).fetchone()
        if row:
            try:
                scope = json.loads(row["scope_json"] or "{}")
                target_files.extend(scope.get("files", []))
            except Exception:
                pass
        _store.close()

    # Deduplicate
    target_files = list(dict.fromkeys(target_files))

    if not target_files:
        return ImpactReport(
            files=[],
            risk="low",
            affected_packages=[],
            likely_tests=[],
            required_commands=[],
            optional_commands=[],
            reasoning=["No files provided."],
        )

    matched_rules: list[_Rule] = []
    for f in target_files:
        matched_rules.extend(_match_rules(f))

    # Deduplicate rules by package
    seen_packages: set[str] = set()
    unique_rules: list[_Rule] = []
    for rule in matched_rules:
        if rule.package not in seen_packages:
            seen_packages.add(rule.package)
            unique_rules.append(rule)

    # Merge commands (preserve order, no duplicates)
    required: list[str] = []
    optional: list[str] = []
    tests: list[str] = []
    packages: list[str] = []
    reasoning: list[str] = []

    _RISK_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    max_risk = 0

    for rule in unique_rules:
        if rule.package not in packages:
            packages.append(rule.package)
        for cmd in rule.required:
            if cmd not in required:
                required.append(cmd)
        for cmd in rule.optional:
            if cmd not in optional:
                optional.append(cmd)
        for t in rule.tests:
            if t not in tests:
                tests.append(t)
        if rule.required:
            reasoning.append(
                f"File in {rule.package!r}: required commands = {rule.required}"
            )
        max_risk = max(max_risk, _RISK_RANK.get(rule.risk, 1))

    risk_names = ["low", "medium", "high", "critical"]
    risk = risk_names[max_risk]

    return ImpactReport(
        files=target_files,
        risk=risk,
        affected_packages=packages,
        likely_tests=tests,
        required_commands=required,
        optional_commands=optional,
        reasoning=reasoning,
    )
