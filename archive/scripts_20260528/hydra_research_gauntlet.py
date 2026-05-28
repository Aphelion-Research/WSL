#!/usr/bin/env python3
"""
Controlled HYDRA non-overlap research gauntlet.

This script orchestrates existing validation scripts. It does not build data,
mutate datasets, add alpha features, or parse console text as truth. Validation
results are read from summary.json files emitted by validate_hydra_nonoverlap.py.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import shlex
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_DATASET = "data/hydra_xauusd_m5_master_clean.parquet"
DEFAULT_OUTPUT_DIR = "reports/hydra_research_gauntlet"
DEFAULT_LABEL = "label_72b"
DEFAULT_RETURN = "fwd_ret_72b"
DEFAULT_HORIZON = 72
DEFAULT_EMBARGO = 288
DEFAULT_THRESHOLDS = [0.55, 0.58, 0.60, 0.62, 0.65, 0.68, 0.70, 0.72]
FAST_THRESHOLDS = [0.55, 0.62, 0.65, 0.68]
DEFAULT_MODELS = ["hist_gradient_boosting", "lightgbm_or_sklearn_fallback"]
FAST_MODELS = ["hist_gradient_boosting"]
DEFAULT_COSTS = [2.0, 5.0, 10.0]
PRIMARY_COST = 2.0

LEADERBOARD_COLUMNS = [
    "stage",
    "dataset",
    "label_column",
    "return_column",
    "horizon_bars",
    "threshold",
    "model",
    "cost_bps",
    "max_rows",
    "folds",
    "process_exit_code",
    "verdict",
    "trade_count",
    "win_rate",
    "avg_trade_return",
    "total_return_gross",
    "total_return_net",
    "max_drawdown",
    "long_count",
    "short_count",
    "best_baseline_name",
    "best_baseline_return_net",
    "excess_over_best_baseline",
    "promoted",
    "promotion_reason",
    "gate_status",
    "summary_json_path",
    "summary_md_path",
    "log_path",
    "command",
]

GATE_PRIORITY = {
    "PERFECT_RESEARCH_OUTPUT": 0,
    "GOOD_RESEARCH_OUTPUT": 1,
    "COST_STRESS_PASS": 2,
    "PROMOTED_TO_FULL": 3,
    "PROMOTED_TO_MEDIUM": 4,
    "SMOKE_SURVIVOR": 5,
    "FAILED_GATE": 6,
    "NO_EDGE": 7,
    "MISSING_SUMMARY": 8,
    "SCRIPT_ERROR": 9,
    "PLANNED": 10,
}

FINAL_VERDICTS = {
    "PREFLIGHT_FAILED",
    "NO_EDGE",
    "SMOKE_ONLY_WEAK",
    "MEDIUM_CANDIDATE",
    "GOOD_RESEARCH_OUTPUT",
    "PERFECT_RESEARCH_OUTPUT",
    "NEEDS_NEW_LABELS",
    "NEEDS_NEW_FEATURES",
    "SCRIPT_ERROR",
    "INTERRUPTED_PARTIAL",
}


class HelpFormatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawDescriptionHelpFormatter,
):
    """Readable examples plus defaults."""


class HeartbeatThread:
    """Prints periodic heartbeat while a subprocess is running."""

    def __init__(self, label: str, log_path: Path, interval: float = 30.0):
        self._label = label
        self._log_path = log_path
        self._interval = interval
        self._start = time.monotonic()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._thread.join(timeout=2.0)

    def _run(self) -> None:
        while not self._stop_event.wait(self._interval):
            elapsed = int(time.monotonic() - self._start)
            print(f"  [heartbeat] still running: {self._label}, elapsed {elapsed}s, log={self._log_path}", flush=True)


@dataclass(frozen=True)
class Config:
    stage: str
    dataset: str
    label_column: str
    return_column: str
    horizon_bars: int
    threshold: float
    model: str
    cost_bps: float
    max_rows: int | None
    folds: int

    def key(self) -> tuple[str, float, str]:
        return (self.model, self.threshold, self.return_column)


@dataclass
class RunContext:
    run_id: str
    run_dir: Path
    logs_dir: Path
    commands_path: Path
    started_utc: str
    git_sha: str
    validation_count: int = 0
    max_configs_reached: bool = False
    interrupted: bool = False
    active_process: subprocess.Popen | None = field(default=None, repr=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a staged HYDRA research gauntlet using existing non-overlap "
            "validation. The goal is baseline-beating evidence, not forced green."
        ),
        formatter_class=HelpFormatter,
        epilog=(
            "Manual use:\n"
            "  python scripts/hydra_research_gauntlet.py --mode fast --output-dir reports/hydra_research_gauntlet_fast\n"
            "  python scripts/hydra_research_gauntlet.py --mode standard --output-dir reports/hydra_research_gauntlet_standard\n"
            "  python scripts/hydra_research_gauntlet.py --mode full --output-dir reports/hydra_research_gauntlet_full\n\n"
            "Dry-run only plans commands and writes planned_commands.sh; it does not execute validation."
        ),
    )
    parser.add_argument("--dataset", default=DEFAULT_DATASET, help="Clean HYDRA dataset path.")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Base report directory.")
    parser.add_argument("--mode", choices=["fast", "standard", "full"], default="standard",
                        help="Gauntlet depth and default search-space size.")
    parser.add_argument("--label-column", default=DEFAULT_LABEL,
                        help="Classification target column passed to non-overlap validation.")
    parser.add_argument("--return-column", default=DEFAULT_RETURN,
                        help="Forward-return/PnL stream passed to non-overlap validation.")
    parser.add_argument("--horizon-bars", type=int, default=DEFAULT_HORIZON,
                        help="Fixed non-overlap hold horizon in bars.")
    parser.add_argument("--max-configs", type=int, default=None,
                        help="Optional cap on validation subprocess configs.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned commands only.")
    parser.add_argument("--no-preflight", action="store_true", help="Skip cheap preflight checks.")
    parser.add_argument("--models", default=None, help="Comma-separated model override.")
    parser.add_argument("--thresholds", default=None, help="Comma-separated threshold override.")
    parser.add_argument("--costs", default=None, help="Comma-separated cost-bps override.")
    parser.add_argument("--seed", type=int, default=42,
                        help="Recorded orchestration seed for reproducibility metadata.")
    parser.add_argument("--resume-run-dir", default=None,
                        help="Path to a previous run directory to resume from. Skips configs that already have summary.json.")
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_id_for(args: argparse.Namespace) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    label = safe_name(args.label_column)
    mode = safe_name(args.mode)
    return f"hydra_gauntlet_{mode}_{label}_{stamp}"


def safe_name(value: Any) -> str:
    text = str(value)
    return "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in text)


def parse_csv_floats(raw: str | None, default: list[float]) -> list[float]:
    if raw is None:
        return list(default)
    values = [float(part.strip()) for part in raw.split(",") if part.strip()]
    if not values:
        raise SystemExit("empty numeric override")
    return values


def parse_csv_strings(raw: str | None, default: list[str]) -> list[str]:
    if raw is None:
        return list(default)
    values = [part.strip() for part in raw.split(",") if part.strip()]
    if not values:
        raise SystemExit("empty string override")
    return values


def git_sha() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return "unknown"
    if result.returncode != 0:
        return "unknown"
    return result.stdout.strip() or "unknown"


def shell_join(command: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in command)


def preflight_commands() -> list[tuple[str, list[str]]]:
    return [
        ("preflight_pycompile_nonoverlap", ["python", "-m", "py_compile", "scripts/validate_hydra_nonoverlap.py"]),
        ("preflight_pycompile_signal", ["python", "-m", "py_compile", "scripts/validate_hydra_signal.py"]),
        ("preflight_clean_dataset", ["python3", "scripts/validate_clean_dataset.py"]),
        ("preflight_regime_leakage", ["python", "-m", "pytest", "tests/test_regime_leakage.py", "-q"]),
        ("preflight_ragd_tests", ["python", "-m", "pytest", "-q", "ragd_embed/tests", "ragd_chunker/tests"]),
    ]


def mode_thresholds(args: argparse.Namespace) -> list[float]:
    if args.thresholds:
        return parse_csv_floats(args.thresholds, DEFAULT_THRESHOLDS)
    if args.mode == "fast":
        return list(FAST_THRESHOLDS)
    return list(DEFAULT_THRESHOLDS)


def mode_models(args: argparse.Namespace) -> list[str]:
    if args.models:
        return parse_csv_strings(args.models, DEFAULT_MODELS)
    if args.mode == "fast":
        return list(FAST_MODELS)
    return list(DEFAULT_MODELS)


def mode_costs(args: argparse.Namespace) -> tuple[float, list[float]]:
    costs = parse_csv_floats(args.costs, DEFAULT_COSTS)
    primary = costs[0] if costs else PRIMARY_COST
    stress = costs[1:] if len(costs) > 1 else [5.0, 10.0]
    return primary, stress


def validation_command(config: Config, stage_output_dir: Path) -> list[str]:
    command = [
        "python",
        "scripts/validate_hydra_nonoverlap.py",
        "--dataset",
        config.dataset,
        "--label-column",
        config.label_column,
        "--return-column",
        config.return_column,
        "--horizon-bars",
        str(config.horizon_bars),
        "--folds",
        str(config.folds),
        "--embargo-bars",
        str(DEFAULT_EMBARGO),
        "--threshold",
        str(config.threshold),
        "--cost-bps",
        str(config.cost_bps),
        "--model",
        config.model,
        "--output-dir",
        str(stage_output_dir),
    ]
    if config.max_rows is not None:
        command.extend(["--max-rows", str(config.max_rows)])
    return command


def planned_smoke_configs(args: argparse.Namespace) -> list[Config]:
    primary_cost, _ = mode_costs(args)
    return [
        Config(
            stage="SMOKE_STAGE",
            dataset=args.dataset,
            label_column=args.label_column,
            return_column=args.return_column,
            horizon_bars=args.horizon_bars,
            threshold=threshold,
            model=model,
            cost_bps=primary_cost,
            max_rows=50_000,
            folds=2,
        )
        for model in mode_models(args)
        for threshold in mode_thresholds(args)
    ]


def medium_config_from(row: dict[str, Any]) -> Config:
    return Config(
        stage="MEDIUM_STAGE",
        dataset=str(row["dataset"]),
        label_column=str(row["label_column"]),
        return_column=str(row["return_column"]),
        horizon_bars=int(row["horizon_bars"]),
        threshold=float(row["threshold"]),
        model=str(row["model"]),
        cost_bps=float(row["cost_bps"]),
        max_rows=100_000,
        folds=3,
    )


def full_config_from(row: dict[str, Any]) -> Config:
    return Config(
        stage="FULL_STAGE",
        dataset=str(row["dataset"]),
        label_column=str(row["label_column"]),
        return_column=str(row["return_column"]),
        horizon_bars=int(row["horizon_bars"]),
        threshold=float(row["threshold"]),
        model=str(row["model"]),
        cost_bps=float(row["cost_bps"]),
        max_rows=None,
        folds=5,
    )


def stress_config_from(row: dict[str, Any], cost_bps: float, mode: str) -> Config:
    standard_controlled = mode == "standard"
    return Config(
        stage="COST_STRESS_STAGE",
        dataset=str(row["dataset"]),
        label_column=str(row["label_column"]),
        return_column=str(row["return_column"]),
        horizon_bars=int(row["horizon_bars"]),
        threshold=float(row["threshold"]),
        model=str(row["model"]),
        cost_bps=float(cost_bps),
        max_rows=100_000 if standard_controlled else None,
        folds=3 if standard_controlled else 5,
    )


def log_name(config: Config) -> str:
    max_rows = "full" if config.max_rows is None else str(config.max_rows)
    return (
        f"{config.stage.lower()}_{safe_name(config.model)}_"
        f"thr_{safe_name(config.threshold)}_cost_{safe_name(config.cost_bps)}_"
        f"rows_{max_rows}.log"
    )


def stage_output_dir(ctx: RunContext, config: Config) -> Path:
    max_rows = "full" if config.max_rows is None else str(config.max_rows)
    dirname = (
        f"{config.stage.lower()}_{safe_name(config.model)}_"
        f"thr_{safe_name(config.threshold)}_cost_{safe_name(config.cost_bps)}_"
        f"rows_{max_rows}"
    )
    return ctx.run_dir / "stage_outputs" / dirname


def append_command(path: Path, command: list[str]) -> None:
    with path.open("a") as handle:
        handle.write(shell_join(command) + "\n")


def run_logged(command: list[str], log_path: Path, ctx: RunContext | None = None, heartbeat_label: str = "") -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    hb = HeartbeatThread(heartbeat_label or "subprocess", log_path) if heartbeat_label else None
    with log_path.open("w") as log:
        log.write(f"$ {shell_join(command)}\n\n")
        log.flush()
        proc = subprocess.Popen(
            command,
            text=True,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        if ctx is not None:
            ctx.active_process = proc
        if hb:
            hb.start()
        try:
            proc.wait()
        finally:
            if hb:
                hb.stop()
            if ctx is not None:
                ctx.active_process = None
        log.write(f"\n[exit_code] {proc.returncode}\n")
    return int(proc.returncode)


def latest_summary(stage_dir: Path, before: set[Path]) -> Path | None:
    if not stage_dir.exists():
        return None
    candidates = [path for path in stage_dir.rglob("summary.json") if path not in before]
    if not candidates:
        candidates = list(stage_dir.rglob("summary.json"))
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def metric(summary: dict[str, Any] | None, key: str) -> Any:
    if not summary:
        return None
    return summary.get("model_results", {}).get(key)


def summary_md_for(summary_path: Path | None) -> str | None:
    if summary_path is None:
        return None
    md = summary_path.with_name("summary.md")
    return str(md) if md.exists() else None


def base_row(config: Config, command: list[str], log_path: Path) -> dict[str, Any]:
    return {
        "stage": config.stage,
        "dataset": config.dataset,
        "label_column": config.label_column,
        "return_column": config.return_column,
        "horizon_bars": config.horizon_bars,
        "threshold": config.threshold,
        "model": config.model,
        "cost_bps": config.cost_bps,
        "max_rows": config.max_rows,
        "folds": config.folds,
        "process_exit_code": None,
        "verdict": None,
        "trade_count": None,
        "win_rate": None,
        "avg_trade_return": None,
        "total_return_gross": None,
        "total_return_net": None,
        "max_drawdown": None,
        "long_count": None,
        "short_count": None,
        "best_baseline_name": None,
        "best_baseline_return_net": None,
        "excess_over_best_baseline": None,
        "promoted": False,
        "promotion_reason": "",
        "gate_status": "PLANNED",
        "summary_json_path": None,
        "summary_md_path": None,
        "log_path": str(log_path),
        "command": shell_join(command),
    }


def row_from_summary(
    config: Config,
    command: list[str],
    log_path: Path,
    exit_code: int,
    summary_path: Path | None,
) -> dict[str, Any]:
    row = base_row(config, command, log_path)
    row["process_exit_code"] = exit_code

    if exit_code != 0:
        row["verdict"] = "SCRIPT_ERROR"
        row["gate_status"] = "SCRIPT_ERROR"
        return row

    if summary_path is None:
        row["verdict"] = "MISSING_SUMMARY"
        row["gate_status"] = "MISSING_SUMMARY"
        return row

    summary = read_json(summary_path)
    if summary is None:
        row["verdict"] = "MISSING_SUMMARY"
        row["gate_status"] = "MISSING_SUMMARY"
        row["summary_json_path"] = str(summary_path)
        row["summary_md_path"] = summary_md_for(summary_path)
        return row

    row.update(
        {
            "verdict": summary.get("verdict"),
            "trade_count": metric(summary, "trade_count"),
            "win_rate": metric(summary, "win_rate"),
            "avg_trade_return": metric(summary, "avg_trade_return"),
            "total_return_gross": metric(summary, "total_return_gross"),
            "total_return_net": metric(summary, "total_return_net"),
            "max_drawdown": metric(summary, "max_drawdown"),
            "long_count": metric(summary, "long_count"),
            "short_count": metric(summary, "short_count"),
            "best_baseline_name": summary.get("best_baseline_name"),
            "best_baseline_return_net": summary.get("best_baseline_return_net"),
            "excess_over_best_baseline": summary.get("excess_over_best_baseline"),
            "summary_json_path": str(summary_path),
            "summary_md_path": summary_md_for(summary_path),
            "gate_status": "NO_EDGE" if summary.get("verdict") == "NO_EDGE" else "FAILED_GATE",
        }
    )
    return row


def as_float(value: Any, default: float | None = None) -> float | None:
    if value is None:
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(number):
        return default
    return number


def as_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def promote_smoke(row: dict[str, Any]) -> tuple[bool, str]:
    trades = as_int(row.get("trade_count"))
    drawdown = as_float(row.get("max_drawdown"))
    net = as_float(row.get("total_return_net"))
    excess = as_float(row.get("excess_over_best_baseline"))

    failures: list[str] = []
    if trades < 100:
        failures.append("too few trades for smoke")
    if drawdown is None or drawdown < -0.20:
        failures.append("smoke drawdown below -0.20")
    if not ((net is not None and net > 0.0) or (excess is not None and excess > -0.03)):
        failures.append("smoke neither net positive nor near baseline")

    if failures:
        return False, "; ".join(failures)
    return True, "smoke promotion gate passed"


def promote_medium(row: dict[str, Any]) -> tuple[bool, str]:
    trades = as_int(row.get("trade_count"))
    net = as_float(row.get("total_return_net"))
    excess = as_float(row.get("excess_over_best_baseline"))
    drawdown = as_float(row.get("max_drawdown"))

    failures: list[str] = []
    if trades < 100:
        failures.append("too few trades for medium")
    if net is None or net <= 0.0:
        failures.append("medium net return not positive")
    if excess is None or excess <= 0.0:
        failures.append("medium baseline dominated")
    if drawdown is None or drawdown < -0.15:
        failures.append("medium drawdown below -0.15")

    if failures:
        return False, "; ".join(failures)
    return True, "medium promotion gate passed"


def is_good_full(row: dict[str, Any]) -> tuple[bool, str]:
    trades = as_int(row.get("trade_count"))
    net = as_float(row.get("total_return_net"))
    excess = as_float(row.get("excess_over_best_baseline"))
    drawdown = as_float(row.get("max_drawdown"))
    win_rate = as_float(row.get("win_rate"))
    verdict = row.get("verdict")

    failures: list[str] = []
    if trades < 500:
        failures.append("full trade count below 500")
    if net is None or net <= 0.0:
        failures.append("full net return not positive")
    if excess is None or excess <= 0.0:
        failures.append("full baseline dominated")
    if drawdown is None or drawdown < -0.12:
        failures.append("full drawdown below -0.12")
    if win_rate is None or win_rate < 0.52:
        failures.append("full win rate below 0.52")
    if verdict == "NO_EDGE":
        failures.append("validator verdict is NO_EDGE")

    if failures:
        return False, "; ".join(failures)
    return True, "GOOD_RESEARCH_OUTPUT gate passed"


def is_stress_5_pass(row: dict[str, Any]) -> bool:
    net = as_float(row.get("total_return_net"))
    excess = as_float(row.get("excess_over_best_baseline"))
    return net is not None and net > 0.0 and excess is not None and excess > 0.0


def is_stress_10_not_catastrophic(row: dict[str, Any]) -> bool:
    net = as_float(row.get("total_return_net"))
    drawdown = as_float(row.get("max_drawdown"))
    if net is None:
        return False
    if net < -0.05:
        return False
    if drawdown is not None and drawdown < -0.20:
        return False
    return True


def annotate_stage_row(row: dict[str, Any]) -> None:
    if row["gate_status"] in {"SCRIPT_ERROR", "MISSING_SUMMARY"}:
        row["promoted"] = False
        row["promotion_reason"] = row["gate_status"]
        return

    if row["stage"] == "SMOKE_STAGE":
        promoted, reason = promote_smoke(row)
        row["promoted"] = promoted
        row["promotion_reason"] = reason
        row["gate_status"] = "PROMOTED_TO_MEDIUM" if promoted else "FAILED_GATE"
    elif row["stage"] == "MEDIUM_STAGE":
        promoted, reason = promote_medium(row)
        row["promoted"] = promoted
        row["promotion_reason"] = reason
        row["gate_status"] = "PROMOTED_TO_FULL" if promoted else "FAILED_GATE"
    elif row["stage"] == "FULL_STAGE":
        good, reason = is_good_full(row)
        row["promoted"] = good
        row["promotion_reason"] = reason
        row["gate_status"] = "GOOD_RESEARCH_OUTPUT" if good else "FAILED_GATE"
    elif row["stage"] == "COST_STRESS_STAGE":
        if as_float(row.get("cost_bps")) == 5.0 and is_stress_5_pass(row):
            row["promoted"] = True
            row["promotion_reason"] = "5 bps cost stress positive and baseline-beating"
            row["gate_status"] = "COST_STRESS_PASS"
        elif as_float(row.get("cost_bps")) == 10.0 and is_stress_10_not_catastrophic(row):
            row["promoted"] = True
            row["promotion_reason"] = "10 bps cost stress not catastrophically negative"
            row["gate_status"] = "COST_STRESS_PASS"
        else:
            row["promoted"] = False
            row["promotion_reason"] = "cost stress failed"
            row["gate_status"] = "FAILED_GATE"


def print_pre_run(config: Config, stage_dir: Path, log_path: Path) -> None:
    max_rows_str = "full" if config.max_rows is None else str(config.max_rows)
    print(
        f"\n{'='*60}\n"
        f"  RUNNING: stage={config.stage} model={config.model}\n"
        f"  threshold={config.threshold} cost_bps={config.cost_bps}\n"
        f"  max_rows={max_rows_str} folds={config.folds}\n"
        f"  output_dir={stage_dir}\n"
        f"  log={log_path}\n"
        f"{'='*60}",
        flush=True,
    )


def print_post_run(exit_code: int, summary_path: Path | None) -> None:
    parts = [f"  exit_code={exit_code}"]
    if summary_path is not None:
        summary = read_json(summary_path)
        if summary:
            parts.append(f"  verdict={summary.get('verdict')}")
            net = metric(summary, "total_return_net")
            excess = summary.get("excess_over_best_baseline")
            dd = metric(summary, "max_drawdown")
            tc = metric(summary, "trade_count")
            parts.append(f"  total_return_net={net}  excess={excess}")
            parts.append(f"  max_drawdown={dd}  trade_count={tc}")
        else:
            parts.append("  summary.json exists but unreadable")
    else:
        parts.append("  no summary.json found")
    print("\n".join(parts), flush=True)


def execute_config(ctx: RunContext, config: Config) -> dict[str, Any] | None:
    if ctx.max_configs_reached:
        return None
    stage_dir = stage_output_dir(ctx, config)
    log_path = ctx.logs_dir / log_name(config)
    command = validation_command(config, stage_dir)

    print_pre_run(config, stage_dir, log_path)

    before = set(stage_dir.rglob("summary.json")) if stage_dir.exists() else set()
    append_command(ctx.commands_path, command)

    heartbeat_label = f"{config.stage}/{config.model}/thr={config.threshold}"
    exit_code = run_logged(command, log_path, ctx=ctx, heartbeat_label=heartbeat_label)
    summary_path = latest_summary(stage_dir, before)

    print_post_run(exit_code, summary_path)

    row = row_from_summary(config, command, log_path, exit_code, summary_path)
    annotate_stage_row(row)

    ctx.validation_count += 1
    return row


def can_run_more(ctx: RunContext, max_configs: int | None) -> bool:
    if max_configs is None:
        return True
    if ctx.validation_count >= max_configs:
        ctx.max_configs_reached = True
        return False
    return True


def sorted_leaderboard(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def sort_key(row: dict[str, Any]) -> tuple[float, float, float, float]:
        gate = GATE_PRIORITY.get(str(row.get("gate_status")), 99)
        excess = as_float(row.get("excess_over_best_baseline"), -math.inf)
        net = as_float(row.get("total_return_net"), -math.inf)
        drawdown = as_float(row.get("max_drawdown"), -math.inf)
        return (gate, -float(excess), -float(net), -float(drawdown))

    return sorted(rows, key=sort_key)


def write_leaderboard(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=LEADERBOARD_COLUMNS)
        writer.writeheader()
        for row in sorted_leaderboard(rows):
            writer.writerow({column: row.get(column) for column in LEADERBOARD_COLUMNS})


def preflight(ctx: RunContext) -> tuple[bool, list[dict[str, Any]]]:
    results: list[dict[str, Any]] = []
    for name, command in preflight_commands():
        log_path = ctx.logs_dir / f"{name}.log"
        append_command(ctx.commands_path, command)
        code = run_logged(command, log_path)
        results.append(
            {
                "name": name,
                "command": shell_join(command),
                "exit_code": code,
                "log_path": str(log_path),
            }
        )
        if code != 0:
            return False, results
    return True, results


def planned_commands(args: argparse.Namespace, ctx: RunContext) -> list[list[str]]:
    commands: list[list[str]] = []
    if not args.no_preflight:
        commands.extend(command for _, command in preflight_commands())
    for config in planned_smoke_configs(args):
        commands.append(validation_command(config, stage_output_dir(ctx, config)))
    return commands


def write_planned_commands(args: argparse.Namespace, ctx: RunContext) -> None:
    commands = planned_commands(args, ctx)
    planned_path = ctx.run_dir / "planned_commands.sh"
    ctx.run_dir.mkdir(parents=True, exist_ok=True)
    with planned_path.open("w") as handle:
        handle.write("#!/usr/bin/env bash\n")
        handle.write("set -euo pipefail\n\n")
        for command in commands:
            handle.write(shell_join(command) + "\n")

    print(f"RUN_ID: {ctx.run_id}")
    print(f"PLANNED_COMMANDS: {planned_path}")
    print("")
    for command in commands:
        print(shell_join(command))


def write_incremental_artifacts(args: argparse.Namespace, ctx: RunContext, rows: list[dict[str, Any]], preflight_results: list[dict[str, Any]]) -> None:
    """Rewrite leaderboard/summary after each completed config so partial progress persists."""
    if not rows:
        return
    write_leaderboard(ctx.run_dir / "leaderboard.csv", rows)
    finalize_full_rows(rows, mode_thresholds(args))
    final_verdict, next_recommendation, decision_reason = final_decision(args, rows, None)
    finished_utc = utc_now()
    write_summary_json(
        ctx.run_dir / "summary.json", args, ctx, rows, preflight_results,
        final_verdict, next_recommendation, decision_reason, finished_utc,
    )
    write_summary_md(
        ctx.run_dir / "summary.md", args, ctx, rows,
        final_verdict, next_recommendation, decision_reason, finished_utc,
    )


def run_gauntlet(args: argparse.Namespace, ctx: RunContext) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str | None]:
    rows: list[dict[str, Any]] = []
    preflight_results: list[dict[str, Any]] = []

    if not args.no_preflight:
        ok, preflight_results = preflight(ctx)
        if not ok:
            return rows, preflight_results, "PREFLIGHT_FAILED"

    try:
        smoke_rows: list[dict[str, Any]] = []
        for config in planned_smoke_configs(args):
            if not can_run_more(ctx, args.max_configs):
                break
            row = execute_config(ctx, config)
            if row is not None:
                rows.append(row)
                smoke_rows.append(row)
                write_incremental_artifacts(args, ctx, rows, preflight_results)

        if args.mode == "fast":
            return rows, preflight_results, None

        medium_rows: list[dict[str, Any]] = []
        for source_row in [row for row in smoke_rows if row.get("promoted")]:
            if not can_run_more(ctx, args.max_configs):
                break
            row = execute_config(ctx, medium_config_from(source_row))
            if row is not None:
                rows.append(row)
                medium_rows.append(row)
                write_incremental_artifacts(args, ctx, rows, preflight_results)

        full_rows_list: list[dict[str, Any]] = []
        for source_row in [row for row in medium_rows if row.get("promoted")]:
            if not can_run_more(ctx, args.max_configs):
                break
            row = execute_config(ctx, full_config_from(source_row))
            if row is not None:
                rows.append(row)
                full_rows_list.append(row)
                write_incremental_artifacts(args, ctx, rows, preflight_results)

        _, stress_costs = mode_costs(args)
        full_survivors = [row for row in full_rows_list if row.get("gate_status") == "GOOD_RESEARCH_OUTPUT"]
        perfect_found = False
        for source_row in full_survivors:
            for cost in stress_costs:
                if not can_run_more(ctx, args.max_configs):
                    break
                row = execute_config(ctx, stress_config_from(source_row, cost, args.mode))
                if row is not None:
                    rows.append(row)
                    write_incremental_artifacts(args, ctx, rows, preflight_results)
            perfect_found, _ = is_perfect(source_row, rows, mode_thresholds(args))
            if perfect_found:
                break

    except KeyboardInterrupt:
        print("\n\n*** INTERRUPTED by Ctrl+C ***", flush=True)
        ctx.interrupted = True
        if ctx.active_process is not None:
            try:
                ctx.active_process.terminate()
                ctx.active_process.wait(timeout=5)
            except Exception:
                pass
            ctx.active_process = None
        write_incremental_artifacts(args, ctx, rows, preflight_results)
        return rows, preflight_results, "INTERRUPTED_PARTIAL"

    return rows, preflight_results, None


def full_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("stage") == "FULL_STAGE"]


def cost_rows_for(rows: list[dict[str, Any]], source: dict[str, Any], cost: float) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if row.get("stage") == "COST_STRESS_STAGE"
        and row.get("model") == source.get("model")
        and as_float(row.get("threshold")) == as_float(source.get("threshold"))
        and as_float(row.get("cost_bps")) == cost
    ]


def neighboring_thresholds_stable(rows: list[dict[str, Any]], source: dict[str, Any], thresholds: list[float]) -> bool:
    full = [
        row
        for row in rows
        if row.get("stage") == "FULL_STAGE"
        and row.get("model") == source.get("model")
        and as_float(row.get("cost_bps")) == as_float(source.get("cost_bps"))
    ]
    current = as_float(source.get("threshold"))
    if current is None:
        return False
    ordered = sorted(set(thresholds))
    if current not in ordered:
        return True
    idx = ordered.index(current)
    neighbor_values = []
    if idx > 0:
        neighbor_values.append(ordered[idx - 1])
    if idx < len(ordered) - 1:
        neighbor_values.append(ordered[idx + 1])
    if len(neighbor_values) < 2:
        return True

    neighbor_rows = [
        row for row in full if as_float(row.get("threshold")) in set(neighbor_values)
    ]
    if len(neighbor_rows) < 2:
        return True
    failures = [row.get("gate_status") != "GOOD_RESEARCH_OUTPUT" for row in neighbor_rows[:2]]
    return not all(failures)


def is_perfect(row: dict[str, Any], rows: list[dict[str, Any]], thresholds: list[float]) -> tuple[bool, str]:
    trades = as_int(row.get("trade_count"))
    net = as_float(row.get("total_return_net"))
    excess = as_float(row.get("excess_over_best_baseline"))
    drawdown = as_float(row.get("max_drawdown"))
    win_rate = as_float(row.get("win_rate"))

    failures: list[str] = []
    if trades < 500:
        failures.append("trade count below 500")
    if net is None or net < 0.15:
        failures.append("total_return_net below 0.15")
    if excess is None or excess < 0.05:
        failures.append("excess over best baseline below 0.05")
    if drawdown is None or drawdown < -0.08:
        failures.append("max_drawdown below -0.08")
    if win_rate is None or win_rate < 0.53:
        failures.append("win_rate below 0.53")

    stress_5 = cost_rows_for(rows, row, 5.0)
    stress_10 = cost_rows_for(rows, row, 10.0)
    if not stress_5 or not any(is_stress_5_pass(stress) for stress in stress_5):
        failures.append("5 bps cost stress not positive and baseline-beating")
    if not stress_10 or not any(is_stress_10_not_catastrophic(stress) for stress in stress_10):
        failures.append("10 bps cost stress catastrophic or missing")
    if not neighboring_thresholds_stable(rows, row, thresholds):
        failures.append("neighboring thresholds both failed")

    if failures:
        return False, "; ".join(failures)
    return True, "PERFECT_RESEARCH_OUTPUT gate passed"


def finalize_full_rows(rows: list[dict[str, Any]], thresholds: list[float]) -> None:
    for row in full_rows(rows):
        if row.get("gate_status") != "GOOD_RESEARCH_OUTPUT":
            continue
        perfect, reason = is_perfect(row, rows, thresholds)
        if perfect:
            row["gate_status"] = "PERFECT_RESEARCH_OUTPUT"
            row["promotion_reason"] = reason


def best_row(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    ranked = sorted_leaderboard([row for row in rows if row.get("summary_json_path")])
    return ranked[0] if ranked else None


def final_decision(
    args: argparse.Namespace,
    rows: list[dict[str, Any]],
    forced_verdict: str | None,
) -> tuple[str, str, str]:
    if forced_verdict == "INTERRUPTED_PARTIAL":
        return "INTERRUPTED_PARTIAL", "RESUME_RUN", "Run interrupted by user. Use --resume-run-dir to continue."

    if forced_verdict == "PREFLIGHT_FAILED":
        return "PREFLIGHT_FAILED", "REJECT_CURRENT_TARGET", "Preflight failed; validation did not run."

    if not rows:
        return "SCRIPT_ERROR", "REJECT_CURRENT_TARGET", "No validation rows were produced."

    if all(row.get("gate_status") in {"SCRIPT_ERROR", "MISSING_SUMMARY"} for row in rows):
        return "SCRIPT_ERROR", "REJECT_CURRENT_TARGET", "All validation subprocesses failed or missed summaries."

    if any(row.get("gate_status") == "PERFECT_RESEARCH_OUTPUT" for row in rows):
        return "PERFECT_RESEARCH_OUTPUT", "PROCEED_TO_BROKER_BACKTEST", (
            "Full non-overlap validation and cost stress met perfect research gates. "
            "Production candidate requires separate broker/event-driven validation."
        )

    if any(row.get("gate_status") == "GOOD_RESEARCH_OUTPUT" for row in rows):
        return "GOOD_RESEARCH_OUTPUT", "PROCEED_TO_BROKER_BACKTEST", (
            "Full non-overlap validation beat baselines under the GOOD gate. "
            "Production candidate requires separate broker/event-driven validation."
        )

    smoke_promoted = any(row.get("stage") == "SMOKE_STAGE" and row.get("promoted") for row in rows)
    medium_promoted = any(row.get("stage") == "MEDIUM_STAGE" and row.get("promoted") for row in rows)
    full_attempted = any(row.get("stage") == "FULL_STAGE" for row in rows)

    if not smoke_promoted:
        return "NO_EDGE", "TRY_NEW_LABEL_DESIGN", (
            "No smoke configs promoted. Positive net alone is insufficient; configs must beat the best baseline."
        )

    if args.mode == "fast":
        return "SMOKE_ONLY_WEAK", "RUN_FULL_GAUNTLET", (
            "Smoke produced at least one promoted candidate, but medium/full gates were not run in fast mode."
        )

    if smoke_promoted and not medium_promoted:
        return "SMOKE_ONLY_WEAK", "TRY_NEW_LABEL_DESIGN", (
            "Smoke candidates failed medium promotion. Given prior overlapping WEAK_EDGE, try label design before feature spam."
        )

    if medium_promoted and not full_attempted:
        return "MEDIUM_CANDIDATE", "RUN_FULL_GAUNTLET", (
            "Medium passed but full validation was not run, likely due to mode or max-configs."
        )

    if medium_promoted and full_attempted:
        return "NEEDS_NEW_LABELS", "TRY_NEW_LABEL_DESIGN", (
            "Medium candidates did not survive full non-overlap gates. Try aligning labels to raw-return PnL target."
        )

    return "NO_EDGE", "TRY_NEW_LABEL_DESIGN", "No baseline-beating non-overlap edge was found."


def failure_analysis(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "net_negative": 0,
        "baseline_dominated": 0,
        "too_much_drawdown": 0,
        "too_few_trades": 0,
        "cost_stress_failed": 0,
        "script_error": 0,
        "missing_summary": 0,
    }
    for row in rows:
        if row.get("gate_status") == "SCRIPT_ERROR":
            counts["script_error"] += 1
        if row.get("gate_status") == "MISSING_SUMMARY":
            counts["missing_summary"] += 1
        if as_float(row.get("total_return_net"), 0.0) is not None and as_float(row.get("total_return_net"), 0.0) < 0:
            counts["net_negative"] += 1
        if as_float(row.get("excess_over_best_baseline"), 0.0) is not None and as_float(row.get("excess_over_best_baseline"), 0.0) <= 0:
            counts["baseline_dominated"] += 1
        if as_float(row.get("max_drawdown")) is not None and as_float(row.get("max_drawdown")) < -0.12:
            counts["too_much_drawdown"] += 1
        if as_int(row.get("trade_count")) < (500 if row.get("stage") == "FULL_STAGE" else 100):
            counts["too_few_trades"] += 1
        if row.get("stage") == "COST_STRESS_STAGE" and row.get("gate_status") == "FAILED_GATE":
            counts["cost_stress_failed"] += 1
    return counts


def stability_summary(rows: list[dict[str, Any]], best: dict[str, Any] | None, thresholds: list[float]) -> dict[str, Any]:
    if best is None:
        return {"best_is_isolated": None, "neighboring_thresholds_checked": []}
    current = as_float(best.get("threshold"))
    ordered = sorted(set(thresholds))
    checked = []
    if current in ordered:
        idx = ordered.index(current)
        for nidx in [idx - 1, idx + 1]:
            if 0 <= nidx < len(ordered):
                threshold = ordered[nidx]
                matches = [
                    row for row in rows
                    if row.get("stage") == best.get("stage")
                    and row.get("model") == best.get("model")
                    and as_float(row.get("threshold")) == threshold
                ]
                checked.extend(
                    {
                        "threshold": threshold,
                        "gate_status": match.get("gate_status"),
                        "total_return_net": match.get("total_return_net"),
                        "excess_over_best_baseline": match.get("excess_over_best_baseline"),
                    }
                    for match in matches[:1]
                )
    if len(checked) < 2:
        isolated = None
    else:
        isolated = all(item.get("gate_status") not in {"GOOD_RESEARCH_OUTPUT", "PERFECT_RESEARCH_OUTPUT"} for item in checked)
    return {"best_is_isolated": isolated, "neighboring_thresholds_checked": checked}


def cost_stress_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "threshold": row.get("threshold"),
            "model": row.get("model"),
            "cost_bps": row.get("cost_bps"),
            "gate_status": row.get("gate_status"),
            "total_return_net": row.get("total_return_net"),
            "excess_over_best_baseline": row.get("excess_over_best_baseline"),
            "max_drawdown": row.get("max_drawdown"),
            "summary_json_path": row.get("summary_json_path"),
        }
        for row in rows
        if row.get("stage") == "COST_STRESS_STAGE"
    ]


def write_summary_json(
    path: Path,
    args: argparse.Namespace,
    ctx: RunContext,
    rows: list[dict[str, Any]],
    preflight_results: list[dict[str, Any]],
    final_verdict: str,
    next_recommendation: str,
    decision_reason: str,
    finished_utc: str,
) -> None:
    best = best_row(rows)
    summary = {
        "run_id": ctx.run_id,
        "git_sha": ctx.git_sha,
        "started_utc": ctx.started_utc,
        "finished_utc": finished_utc,
        "mode": args.mode,
        "seed": args.seed,
        "dataset": args.dataset,
        "label_column": args.label_column,
        "return_column": args.return_column,
        "horizon_bars": args.horizon_bars,
        "total_configs_run": ctx.validation_count,
        "max_configs_reached": ctx.max_configs_reached,
        "final_verdict": final_verdict,
        "next_recommendation": next_recommendation,
        "decision_reason": decision_reason,
        "production_warning": "Production candidate requires separate broker/event-driven validation.",
        "preflight": preflight_results,
        "best_config": best,
        "failure_analysis": failure_analysis(rows),
        "cost_stress_results": cost_stress_summary(rows),
        "stability_analysis": stability_summary(rows, best, mode_thresholds(args)),
        "leaderboard_csv": str(ctx.run_dir / "leaderboard.csv"),
    }
    path.write_text(json.dumps(summary, indent=2, default=str) + "\n")


def md_value(value: Any, digits: int = 6) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def write_summary_md(
    path: Path,
    args: argparse.Namespace,
    ctx: RunContext,
    rows: list[dict[str, Any]],
    final_verdict: str,
    next_recommendation: str,
    decision_reason: str,
    finished_utc: str,
) -> None:
    best = best_row(rows)
    top10 = sorted_leaderboard(rows)[:10]
    failures = failure_analysis(rows)
    stress = cost_stress_summary(rows)
    stability = stability_summary(rows, best, mode_thresholds(args))

    lines = [
        "# HYDRA Research Gauntlet Summary",
        "",
        "## Run metadata",
        "",
        f"- run_id: `{ctx.run_id}`",
        f"- git sha: `{ctx.git_sha}`",
        f"- started UTC: {ctx.started_utc}",
        f"- finished UTC: {finished_utc}",
        f"- mode: `{args.mode}`",
        f"- dataset: `{args.dataset}`",
        f"- label/return/horizon: `{args.label_column}` / `{args.return_column}` / {args.horizon_bars}",
        f"- total configs run: {ctx.validation_count}",
        "",
        "## Final verdict",
        "",
        f"- verdict: `{final_verdict}`",
        f"- next recommendation: `{next_recommendation}`",
        f"- reason: {decision_reason}",
        "",
    ]

    if best:
        lines.extend(
            [
                "## Best config",
                "",
                f"- threshold: {best.get('threshold')}",
                f"- model: `{best.get('model')}`",
                f"- stage: `{best.get('stage')}`",
                f"- cost: {best.get('cost_bps')}",
                f"- total_return_net: {md_value(best.get('total_return_net'))}",
                f"- excess_over_best_baseline: {md_value(best.get('excess_over_best_baseline'))}",
                f"- win_rate: {md_value(best.get('win_rate'), 4)}",
                f"- max_drawdown: {md_value(best.get('max_drawdown'))}",
                f"- trade_count: {best.get('trade_count')}",
                "",
            ]
        )
    else:
        lines.extend(["## Best config", "", "No valid best config.", ""])

    lines.extend(["## Top 10 leaderboard", ""])
    if top10:
        lines.append("| rank | stage | model | threshold | cost | net | excess | drawdown | trades | gate | verdict |")
        lines.append("|---:|---|---|---:|---:|---:|---:|---:|---:|---|---|")
        for idx, row in enumerate(top10, start=1):
            lines.append(
                "| "
                f"{idx} | {row.get('stage')} | {row.get('model')} | {row.get('threshold')} | "
                f"{row.get('cost_bps')} | {md_value(row.get('total_return_net'))} | "
                f"{md_value(row.get('excess_over_best_baseline'))} | {md_value(row.get('max_drawdown'))} | "
                f"{row.get('trade_count')} | {row.get('gate_status')} | {row.get('verdict')} |"
            )
    else:
        lines.append("No validation rows.")

    lines.extend(
        [
            "",
            "## Failed-gate analysis",
            "",
            f"- net negative: {failures['net_negative']}",
            f"- baseline dominated: {failures['baseline_dominated']}",
            f"- too much drawdown: {failures['too_much_drawdown']}",
            f"- too few trades: {failures['too_few_trades']}",
            f"- cost stress failed: {failures['cost_stress_failed']}",
            f"- subprocess errors: {failures['script_error']}",
            f"- missing summaries: {failures['missing_summary']}",
            "",
            "## Cost stress results",
            "",
        ]
    )

    if stress:
        lines.append("| model | threshold | cost | net | excess | drawdown | gate |")
        lines.append("|---|---:|---:|---:|---:|---:|---|")
        for row in stress:
            lines.append(
                f"| {row.get('model')} | {row.get('threshold')} | {row.get('cost_bps')} | "
                f"{md_value(row.get('total_return_net'))} | {md_value(row.get('excess_over_best_baseline'))} | "
                f"{md_value(row.get('max_drawdown'))} | {row.get('gate_status')} |"
            )
    else:
        lines.append("No cost stress runs were eligible or executed.")

    lines.extend(
        [
            "",
            "## Stability analysis",
            "",
            f"- best result isolated: {stability['best_is_isolated']}",
            f"- neighboring thresholds: `{json.dumps(stability['neighboring_thresholds_checked'], default=str)}`",
            "",
            "## Warning",
            "",
            "This is still bar-return validation, not broker/event-driven execution.",
            "Production candidate requires separate broker/event-driven validation.",
            "",
            "## Next recommendation",
            "",
            next_recommendation,
            "",
        ]
    )

    path.write_text("\n".join(lines))


def stage_output_dir_for_config_in_dir(run_dir: Path, config: Config) -> Path:
    """Compute stage_output_dir without requiring a RunContext."""
    max_rows = "full" if config.max_rows is None else str(config.max_rows)
    dirname = (
        f"{config.stage.lower()}_{safe_name(config.model)}_"
        f"thr_{safe_name(config.threshold)}_cost_{safe_name(config.cost_bps)}_"
        f"rows_{max_rows}"
    )
    return run_dir / "stage_outputs" / dirname


def load_existing_rows(run_dir: Path) -> list[dict[str, Any]]:
    """Load leaderboard rows from existing stage_output summary.json files."""
    rows: list[dict[str, Any]] = []
    stage_outputs = run_dir / "stage_outputs"
    if not stage_outputs.exists():
        return rows
    for summary_path in stage_outputs.rglob("summary.json"):
        summary = read_json(summary_path)
        if summary is None:
            continue
        row = {
            "stage": summary.get("stage", "UNKNOWN"),
            "dataset": summary.get("dataset", ""),
            "label_column": summary.get("label_column", ""),
            "return_column": summary.get("return_column", ""),
            "horizon_bars": summary.get("horizon_bars", 0),
            "threshold": summary.get("threshold"),
            "model": summary.get("model"),
            "cost_bps": summary.get("cost_bps"),
            "max_rows": summary.get("max_rows"),
            "folds": summary.get("folds"),
            "process_exit_code": 0,
            "verdict": summary.get("verdict"),
            "trade_count": metric(summary, "trade_count"),
            "win_rate": metric(summary, "win_rate"),
            "avg_trade_return": metric(summary, "avg_trade_return"),
            "total_return_gross": metric(summary, "total_return_gross"),
            "total_return_net": metric(summary, "total_return_net"),
            "max_drawdown": metric(summary, "max_drawdown"),
            "long_count": metric(summary, "long_count"),
            "short_count": metric(summary, "short_count"),
            "best_baseline_name": summary.get("best_baseline_name"),
            "best_baseline_return_net": summary.get("best_baseline_return_net"),
            "excess_over_best_baseline": summary.get("excess_over_best_baseline"),
            "promoted": False,
            "promotion_reason": "",
            "gate_status": "PLANNED",
            "summary_json_path": str(summary_path),
            "summary_md_path": summary_md_for(summary_path),
            "log_path": None,
            "command": None,
        }
        annotate_stage_row(row)
        rows.append(row)
    return rows


def config_already_done(run_dir: Path, config: Config) -> bool:
    """Check if a config's stage_output_dir already has summary.json."""
    stage_dir = stage_output_dir_for_config_in_dir(run_dir, config)
    return any(stage_dir.rglob("summary.json"))


def initialize_context(args: argparse.Namespace) -> RunContext:
    run_id = run_id_for(args)
    run_dir = Path(args.output_dir) / run_id
    logs_dir = run_dir / "logs"
    run_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    commands_path = run_dir / "commands_run.sh"
    commands_path.write_text("#!/usr/bin/env bash\nset -euo pipefail\n\n")
    return RunContext(
        run_id=run_id,
        run_dir=run_dir,
        logs_dir=logs_dir,
        commands_path=commands_path,
        started_utc=utc_now(),
        git_sha=git_sha(),
    )


def initialize_resume_context(args: argparse.Namespace) -> RunContext:
    """Create a RunContext that reuses an existing run directory."""
    run_dir = Path(args.resume_run_dir)
    if not run_dir.exists():
        raise SystemExit(f"Resume dir does not exist: {run_dir}")
    logs_dir = run_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    commands_path = run_dir / "commands_run.sh"
    run_id = run_dir.name
    return RunContext(
        run_id=run_id,
        run_dir=run_dir,
        logs_dir=logs_dir,
        commands_path=commands_path,
        started_utc=utc_now(),
        git_sha=git_sha(),
    )


def run_gauntlet_with_resume(args: argparse.Namespace, ctx: RunContext) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str | None]:
    """Run gauntlet, skipping configs whose stage_output already has summary.json."""
    rows: list[dict[str, Any]] = []
    preflight_results: list[dict[str, Any]] = []

    existing_rows = load_existing_rows(ctx.run_dir)
    rows.extend(existing_rows)
    ctx.validation_count = len(existing_rows)
    print(f"  [resume] loaded {len(existing_rows)} existing results from {ctx.run_dir / 'stage_outputs'}", flush=True)

    if not args.no_preflight:
        ok, preflight_results = preflight(ctx)
        if not ok:
            return rows, preflight_results, "PREFLIGHT_FAILED"

    try:
        smoke_rows: list[dict[str, Any]] = [r for r in rows if r.get("stage") == "SMOKE_STAGE"]
        for config in planned_smoke_configs(args):
            if not can_run_more(ctx, args.max_configs):
                break
            if config_already_done(ctx.run_dir, config):
                continue
            row = execute_config(ctx, config)
            if row is not None:
                rows.append(row)
                smoke_rows.append(row)
                write_incremental_artifacts(args, ctx, rows, preflight_results)

        if args.mode == "fast":
            return rows, preflight_results, None

        medium_rows: list[dict[str, Any]] = [r for r in rows if r.get("stage") == "MEDIUM_STAGE"]
        for source_row in [row for row in smoke_rows if row.get("promoted")]:
            if not can_run_more(ctx, args.max_configs):
                break
            cfg = medium_config_from(source_row)
            if config_already_done(ctx.run_dir, cfg):
                continue
            row = execute_config(ctx, cfg)
            if row is not None:
                rows.append(row)
                medium_rows.append(row)
                write_incremental_artifacts(args, ctx, rows, preflight_results)

        full_rows_list: list[dict[str, Any]] = [r for r in rows if r.get("stage") == "FULL_STAGE"]
        for source_row in [row for row in medium_rows if row.get("promoted")]:
            if not can_run_more(ctx, args.max_configs):
                break
            cfg = full_config_from(source_row)
            if config_already_done(ctx.run_dir, cfg):
                continue
            row = execute_config(ctx, cfg)
            if row is not None:
                rows.append(row)
                full_rows_list.append(row)
                write_incremental_artifacts(args, ctx, rows, preflight_results)

        _, stress_costs = mode_costs(args)
        full_survivors = [row for row in full_rows_list if row.get("gate_status") == "GOOD_RESEARCH_OUTPUT"]
        perfect_found = False
        for source_row in full_survivors:
            for cost in stress_costs:
                if not can_run_more(ctx, args.max_configs):
                    break
                cfg = stress_config_from(source_row, cost, args.mode)
                if config_already_done(ctx.run_dir, cfg):
                    continue
                row = execute_config(ctx, cfg)
                if row is not None:
                    rows.append(row)
                    write_incremental_artifacts(args, ctx, rows, preflight_results)
            perfect_found, _ = is_perfect(source_row, rows, mode_thresholds(args))
            if perfect_found:
                break

    except KeyboardInterrupt:
        print("\n\n*** INTERRUPTED by Ctrl+C ***", flush=True)
        ctx.interrupted = True
        if ctx.active_process is not None:
            try:
                ctx.active_process.terminate()
                ctx.active_process.wait(timeout=5)
            except Exception:
                pass
            ctx.active_process = None
        write_incremental_artifacts(args, ctx, rows, preflight_results)
        return rows, preflight_results, "INTERRUPTED_PARTIAL"

    return rows, preflight_results, None


def main() -> int:
    args = parse_args()

    if args.resume_run_dir:
        ctx = initialize_resume_context(args)
        print(f"RESUMING: {ctx.run_dir}", flush=True)
    else:
        ctx = initialize_context(args)

    if args.max_configs is not None and args.max_configs <= 0:
        raise SystemExit("--max-configs must be positive when provided")
    if args.dry_run:
        write_planned_commands(args, ctx)
        return 0

    if args.resume_run_dir:
        rows, preflight_results, forced_verdict = run_gauntlet_with_resume(args, ctx)
    else:
        rows, preflight_results, forced_verdict = run_gauntlet(args, ctx)

    finalize_full_rows(rows, mode_thresholds(args))
    final_verdict, next_recommendation, decision_reason = final_decision(args, rows, forced_verdict)
    if final_verdict not in FINAL_VERDICTS:
        final_verdict = "SCRIPT_ERROR"
        next_recommendation = "REJECT_CURRENT_TARGET"
        decision_reason = "Internal verdict mapping failed."

    finished_utc = utc_now()
    write_leaderboard(ctx.run_dir / "leaderboard.csv", rows)
    write_summary_json(
        ctx.run_dir / "summary.json",
        args,
        ctx,
        rows,
        preflight_results,
        final_verdict,
        next_recommendation,
        decision_reason,
        finished_utc,
    )
    write_summary_md(
        ctx.run_dir / "summary.md",
        args,
        ctx,
        rows,
        final_verdict,
        next_recommendation,
        decision_reason,
        finished_utc,
    )

    print(f"\nRUN_ID: {ctx.run_id}")
    print(f"VERDICT: {final_verdict}")
    print(f"NEXT: {next_recommendation}")
    print(f"LEADERBOARD: {ctx.run_dir / 'leaderboard.csv'}")
    print(f"SUMMARY_JSON: {ctx.run_dir / 'summary.json'}")
    print(f"SUMMARY_MD: {ctx.run_dir / 'summary.md'}")

    if ctx.interrupted:
        print(f"\nRUN_DIR (for resume): {ctx.run_dir}", flush=True)
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
