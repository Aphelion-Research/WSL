"""Benchmark harness for dominion_loader (F18).

Runs labeled suites, measures p50/p95/p99, writes JSON to reports/benchmarks/.

Usage:
  dominion bench --suite foundation --runs 3 --out reports/benchmarks/foundation-<ts>.json

Result schema:
  {
    "suite": "foundation",
    "runs": 3,
    "git_commit": "...",
    "timestamp": "...",
    "metrics": {
      "cold_scan_s":  {"p50": ..., "p95": ...},
      "warm_scan_s":  {"p50": ..., "p95": ...},
      ...
    }
  }

INTERFACE(agent-1): run_suite()  (benchmark results are evidence for performance claims)
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional


@dataclass
class BenchResult:
    """Result of one benchmark metric across multiple runs."""
    name: str
    runs: list[float]
    unit: str

    @property
    def p50(self) -> float:
        return _percentile(self.runs, 50)

    @property
    def p95(self) -> float:
        return _percentile(self.runs, 95)

    @property
    def p99(self) -> float:
        return _percentile(self.runs, 99)

    def to_dict(self) -> dict:
        return {
            "p50": round(self.p50, 4),
            "p95": round(self.p95, 4),
            "p99": round(self.p99, 4),
            "mean": round(sum(self.runs) / len(self.runs), 4) if self.runs else 0.0,
            "min": round(min(self.runs), 4) if self.runs else 0.0,
            "max": round(max(self.runs), 4) if self.runs else 0.0,
            "n": len(self.runs),
            "unit": self.unit,
        }


# Registry of suites: name → bench function
_SUITES: dict[str, Callable[[int], dict[str, BenchResult]]] = {}


def register_suite(name: str, fn: Callable[[int], dict[str, BenchResult]]) -> None:
    """Register a benchmark suite."""
    _SUITES[name] = fn


def run_suite(
    suite_name: str,
    *,
    runs: int = 3,
    out_dir: Optional[Path | str] = None,
) -> dict[str, Any]:
    """Run a named benchmark suite and write JSON results.

    Returns the full result dict.
    Raises KeyError if suite is not registered.
    """
    if suite_name not in _SUITES:
        raise KeyError(f"Unknown benchmark suite '{suite_name}'. Available: {list(_SUITES)}")

    if out_dir is None:
        dominion_root = Path(os.environ.get("DOMINION_ROOT", str(Path.home() / "Dominion")))
        out_dir = dominion_root / "reports" / "benchmarks"
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    git_commit = _git_commit()

    metrics = _SUITES[suite_name](runs)

    result = {
        "suite": suite_name,
        "runs": runs,
        "git_commit": git_commit,
        "timestamp": ts,
        "metrics": {name: m.to_dict() for name, m in metrics.items()},
    }

    out_path = out_dir / f"{suite_name}-{ts}.json"
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    return result


def list_suites() -> list[str]:
    """List registered benchmark suite names."""
    return list(_SUITES.keys())


# ---------------------------------------------------------------------------
# Foundation suite
# ---------------------------------------------------------------------------
def _run_foundation_suite(runs: int) -> dict[str, BenchResult]:
    """Run the foundation benchmark suite."""
    import resource
    from dominion_loader.scan import scan, iter_loaded_files
    from dominion_loader.ignore import Ignore
    from dominion_loader.manifest import Manifest

    dominion_root = Path(os.environ.get("DOMINION_ROOT", str(Path.home() / "Dominion")))

    cold_times: list[float] = []
    warm_times: list[float] = []
    files_per_sec_list: list[float] = []
    mb_per_sec_list: list[float] = []
    peak_rss_list: list[float] = []

    for _ in range(runs):
        # Cold scan: fresh temp manifest
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_manifest_db = Path(tmpdir) / "manifest.db"
            os.environ["DOMINION_HOME"] = tmpdir
            os.environ["DOMINION_TRACE"] = "off"  # don't pollute traces during bench
            os.environ["DOMINION_RAGD_BRIDGE"] = "off"

            manifest = Manifest(tmp_manifest_db)
            start = time.monotonic()
            stats = scan(
                dominion_root,
                dry_run=False,
                manifest=manifest,
                trace_id="bench",
            )
            elapsed = time.monotonic() - start
            cold_times.append(elapsed)

            total_files = stats.files_seen
            # Approximate MB from manifest
            total_mb = 0.0
            for entry in manifest.list_active():
                total_mb += entry.size / (1024 * 1024)

            if elapsed > 0 and total_files > 0:
                files_per_sec_list.append(total_files / elapsed)
                mb_per_sec_list.append(total_mb / elapsed)

            # Warm scan (same manifest, no changes)
            start = time.monotonic()
            scan(
                dominion_root,
                dry_run=False,
                manifest=manifest,
                trace_id="bench-warm",
            )
            warm_times.append(time.monotonic() - start)

            manifest.close()

        # Reset env
        os.environ.pop("DOMINION_HOME", None)
        os.environ.pop("DOMINION_TRACE", None)
        os.environ.pop("DOMINION_RAGD_BRIDGE", None)

        # Peak RSS (Linux)
        try:
            rss_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            peak_rss_list.append(rss_kb * 1024)
        except Exception:
            peak_rss_list.append(0)

    return {
        "cold_scan_s": BenchResult("cold_scan_s", cold_times, "seconds"),
        "warm_scan_s": BenchResult("warm_scan_s", warm_times, "seconds"),
        "files_per_sec": BenchResult("files_per_sec", files_per_sec_list, "files/s"),
        "mb_per_sec": BenchResult("mb_per_sec", mb_per_sec_list, "MB/s"),
        "peak_rss_bytes": BenchResult("peak_rss_bytes", peak_rss_list, "bytes"),
    }


register_suite("foundation", _run_foundation_suite)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    sv = sorted(values)
    idx = min(int(len(sv) * p / 100), len(sv) - 1)
    return sv[idx]


def _git_commit() -> str:
    """Return the current git commit hash, or 'unknown'."""
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        return out.decode("utf-8").strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        return "unknown"
