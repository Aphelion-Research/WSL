#!/usr/bin/env python3
"""
HYDRA label-design lab.

This script derives research-only label datasets under reports/hydra_label_lab.
It does not mutate data/, rebuild canonical datasets, train models, or run the
HYDRA research gauntlet.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import shlex
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


DEFAULT_DATASET = "data/hydra_xauusd_m5_master_clean.parquet"
DEFAULT_OUTPUT_DIR = "reports/hydra_label_lab"
DEFAULT_COST_BPS_LIST = "2,5"
DEFAULT_MODE = "fast"

HIGH_CANDIDATES = ("high", "A_high", "xau_high", "XAUUSD_high", "bid_high", "mid_high")
LOW_CANDIDATES = ("low", "A_low", "xau_low", "XAUUSD_low", "bid_low", "mid_low")
CLOSE_CANDIDATES = ("close", "A_close", "xau_close", "XAUUSD_close", "bid_close", "mid_close")

CANDIDATE_COLUMNS = [
    "candidate",
    "available",
    "unavailable_reason",
    "dataset_path",
    "metadata_path",
    "label_column",
    "return_column",
    "horizon_bars",
    "cost_bps",
    "row_count",
    "positive_rate",
    "nan_rate",
    "return_mean",
    "return_std",
    "return_min",
    "return_max",
    "label_return_sign_mismatch",
    "recommended_gauntlet_command",
    "dry_run_gauntlet_command",
]


class HelpFormatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawDescriptionHelpFormatter,
):
    """Readable examples plus defaults."""


@dataclass(frozen=True)
class CandidateSpec:
    name: str
    label_column: str
    return_column: str
    horizon_bars: int
    kind: str
    cost_bps: float | None = None
    conditional_reason: str | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create derived HYDRA label-design research datasets under reports/. "
            "No training, canonical data mutation, or gauntlet validation is run."
        ),
        formatter_class=HelpFormatter,
        epilog=(
            "Examples:\n"
            "  python scripts/hydra_label_design_lab.py --dry-run\n"
            "  python scripts/hydra_label_design_lab.py --output-dir reports/hydra_label_lab\n\n"
            "The generated planned_gauntlet_commands.sh uses gauntlet --dry-run commands only."
        ),
    )
    parser.add_argument("--dataset", default=DEFAULT_DATASET, help="Source clean HYDRA dataset.")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR,
                        help="Base output directory; must resolve to reports/hydra_label_lab.")
    parser.add_argument("--max-rows", type=int, default=None,
                        help="Optional first-N row cap for smoke dataset generation.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print planned candidates and commands without writing parquet.")
    parser.add_argument("--cost-bps-list", default=DEFAULT_COST_BPS_LIST,
                        help="Comma-separated cost thresholds for cost-aware sign labels.")
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"hydra_label_lab_{stamp}"


def safe_name(value: Any) -> str:
    text = str(value)
    return "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in text)


def shell_join(command: list[str]) -> str:
    return " ".join(shlex.quote(str(part)) for part in command)


def parse_costs(raw: str) -> list[float]:
    values: list[float] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        value = float(part)
        if value <= 0:
            raise SystemExit("--cost-bps-list values must be positive")
        values.append(value)
    if not values:
        raise SystemExit("--cost-bps-list must contain at least one positive value")
    return values


def cost_label_suffix(cost_bps: float) -> str:
    if math.isclose(cost_bps, 2.0):
        return ""
    value = int(cost_bps) if float(cost_bps).is_integer() else str(cost_bps).replace(".", "p")
    return f"_{value}bps"


def cost_candidate_name(prefix: str, horizon: int, cost_bps: float) -> str:
    if math.isclose(cost_bps, 2.0):
        return f"{prefix}_cost_aware_sign_{horizon}b"
    if math.isclose(cost_bps, 5.0):
        return f"{prefix}_stronger_cost_aware_sign_{horizon}b"
    return f"{prefix}_cost_aware_sign_{horizon}b{cost_label_suffix(cost_bps)}"


def validate_output_dir(output_dir: str) -> Path:
    allowed = (Path.cwd() / DEFAULT_OUTPUT_DIR).resolve()
    requested = Path(output_dir)
    resolved = requested.resolve() if requested.is_absolute() else (Path.cwd() / requested).resolve()
    if resolved != allowed:
        raise SystemExit(
            "output-dir is restricted to reports/hydra_label_lab so derived datasets stay out of data/"
        )
    return Path(DEFAULT_OUTPUT_DIR)


def find_column(columns: list[str], candidates: tuple[str, ...]) -> str | None:
    lower_map = {column.lower(): column for column in columns}
    for candidate in candidates:
        found = lower_map.get(candidate.lower())
        if found is not None:
            return found
    return None


def candidate_specs(costs: list[float], include_20b: bool = True) -> list[CandidateSpec]:
    specs = [
        CandidateSpec(
            name="raw_sign_72b",
            label_column="lab_raw_sign_72b",
            return_column="fwd_ret_72b",
            horizon_bars=72,
            kind="raw_sign",
        ),
    ]

    for cost in costs:
        suffix = cost_label_suffix(cost)
        specs.append(
            CandidateSpec(
                name=cost_candidate_name("", 72, cost).lstrip("_"),
                label_column=f"lab_cost_sign_72b{suffix}",
                return_column="fwd_ret_72b",
                horizon_bars=72,
                kind="cost_sign",
                cost_bps=cost,
            )
        )

    specs.append(
        CandidateSpec(
            name="triple_barrier_aligned_72b",
            label_column="label_72b",
            return_column="tb_ret_72b",
            horizon_bars=72,
            kind="triple_barrier_aligned",
            conditional_reason="requires label_72b and computable ATR from high/low/close",
        )
    )

    if include_20b:
        specs.append(
            CandidateSpec(
                name="raw_sign_20b",
                label_column="lab_raw_sign_20b",
                return_column="fwd_ret_20b",
                horizon_bars=20,
                kind="raw_sign",
                conditional_reason="requires fwd_ret_20b",
            )
        )
        for cost in costs:
            suffix = cost_label_suffix(cost)
            specs.append(
                CandidateSpec(
                    name=cost_candidate_name("", 20, cost).lstrip("_"),
                    label_column=f"lab_cost_sign_20b{suffix}",
                    return_column="fwd_ret_20b",
                    horizon_bars=20,
                    kind="cost_sign",
                    cost_bps=cost,
                    conditional_reason="requires fwd_ret_20b",
                )
            )
    return specs


def require_deps():
    try:
        import numpy as np
        import pandas as pd
    except ImportError as exc:
        raise SystemExit(f"missing dependency: {exc.name}") from exc
    return np, pd


def load_dataset(path: Path, max_rows: int | None):
    _, pd = require_deps()
    if not path.exists():
        raise SystemExit(f"dataset not found: {path}")
    df = pd.read_parquet(path)
    if max_rows is not None:
        if max_rows <= 0:
            raise SystemExit("--max-rows must be positive when provided")
        df = df.iloc[:max_rows].copy()
    if df.empty:
        raise SystemExit("dataset has zero rows")
    return df


def raw_sign_label(df, return_column: str):
    _, pd = require_deps()
    ret = pd.to_numeric(df[return_column], errors="coerce")
    return (ret > 0).astype("int8")


def cost_sign_label(df, return_column: str, cost_bps: float):
    np, pd = require_deps()
    ret = pd.to_numeric(df[return_column], errors="coerce")
    threshold = cost_bps / 10_000.0
    label = pd.Series(np.nan, index=df.index, dtype="float64")
    label.loc[ret > threshold] = 1.0
    label.loc[ret < -threshold] = 0.0
    return label


def compute_atr_pct(df):
    np, pd = require_deps()
    columns = list(df.columns)
    high_col = find_column(columns, HIGH_CANDIDATES)
    low_col = find_column(columns, LOW_CANDIDATES)
    close_col = find_column(columns, CLOSE_CANDIDATES)
    if not high_col or not low_col or not close_col:
        return None, {
            "reason": "missing high/low/close columns",
            "high_column": high_col,
            "low_column": low_col,
            "close_column": close_col,
        }

    high = pd.to_numeric(df[high_col], errors="coerce")
    low = pd.to_numeric(df[low_col], errors="coerce")
    close = pd.to_numeric(df[close_col], errors="coerce")
    prev_close = close.shift(1)
    true_range = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = true_range.rolling(window=14, min_periods=14).mean()
    atr_pct = atr / close.abs().replace(0, np.nan)
    atr_pct = atr_pct.replace([np.inf, -np.inf], np.nan)
    if atr_pct.notna().sum() == 0:
        return None, {
            "reason": "ATR produced no finite values",
            "high_column": high_col,
            "low_column": low_col,
            "close_column": close_col,
        }
    return atr_pct, {
        "reason": None,
        "high_column": high_col,
        "low_column": low_col,
        "close_column": close_col,
        "atr_period": 14,
    }


def triple_barrier_return(df):
    np, pd = require_deps()
    if "label_72b" not in df.columns:
        return None, {"reason": "label_72b not found"}
    atr_pct, atr_meta = compute_atr_pct(df)
    if atr_pct is None:
        return None, atr_meta

    label = pd.to_numeric(df["label_72b"], errors="coerce")
    tb_ret = pd.Series(np.nan, index=df.index, dtype="float64")
    tb_ret.loc[label == 1] = 1.5 * atr_pct.loc[label == 1]
    tb_ret.loc[label == 0] = -1.5 * atr_pct.loc[label == 0]
    tb_ret = tb_ret.replace([np.inf, -np.inf], np.nan)
    if tb_ret.notna().sum() == 0:
        meta = dict(atr_meta)
        meta["reason"] = "tb_ret_72b produced no finite values"
        return None, meta
    return tb_ret, atr_meta


def transform_candidate(df, spec: CandidateSpec) -> tuple[dict[str, Any], Callable[[Any], Any] | None]:
    columns = set(df.columns)
    if spec.kind in {"raw_sign", "cost_sign"} and spec.return_column not in columns:
        return {"available": False, "unavailable_reason": f"{spec.return_column} not found"}, None

    if spec.kind == "raw_sign":
        return {"available": True}, lambda frame: raw_sign_label(frame, spec.return_column)
    if spec.kind == "cost_sign":
        if spec.cost_bps is None:
            return {"available": False, "unavailable_reason": "missing cost threshold"}, None
        return {"available": True}, lambda frame: cost_sign_label(frame, spec.return_column, spec.cost_bps)
    if spec.kind == "triple_barrier_aligned":
        tb_ret, meta = triple_barrier_return(df)
        if tb_ret is None:
            return {"available": False, "unavailable_reason": meta.get("reason"), "atr": meta}, None
        return {"available": True, "atr": meta, "tb_ret": tb_ret}, None

    return {"available": False, "unavailable_reason": f"unknown candidate kind: {spec.kind}"}, None


def metric_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(result):
        return None
    return result


def summarize_candidate(df, spec: CandidateSpec) -> dict[str, Any]:
    _, pd = require_deps()
    label = pd.to_numeric(df[spec.label_column], errors="coerce")
    returns = pd.to_numeric(df[spec.return_column], errors="coerce")
    valid = label.notna() & returns.notna()
    label_non_null = label.dropna()
    valid_returns = returns.loc[valid]
    sign_valid = valid & (returns != 0)

    mismatch = None
    if sign_valid.any():
        expected = (returns.loc[sign_valid] > 0).astype("int8")
        actual = label.loc[sign_valid].astype("int8")
        mismatch = metric_float((actual != expected).mean())

    return {
        "row_count": int(valid.sum()),
        "positive_rate": metric_float((label_non_null == 1).mean()) if len(label_non_null) else None,
        "nan_rate": metric_float(label.isna().mean()),
        "return_mean": metric_float(valid_returns.mean()) if len(valid_returns) else None,
        "return_std": metric_float(valid_returns.std()) if len(valid_returns) else None,
        "return_min": metric_float(valid_returns.min()) if len(valid_returns) else None,
        "return_max": metric_float(valid_returns.max()) if len(valid_returns) else None,
        "label_return_sign_mismatch": mismatch,
    }


def gauntlet_commands(dataset_path: Path, spec: CandidateSpec) -> tuple[str, str]:
    output_dir = f"reports/hydra_research_gauntlet_{safe_name(spec.name)}"
    command = [
        "python",
        "scripts/hydra_research_gauntlet.py",
        "--mode",
        DEFAULT_MODE,
        "--dataset",
        str(dataset_path),
        "--label-column",
        spec.label_column,
        "--return-column",
        spec.return_column,
        "--horizon-bars",
        str(spec.horizon_bars),
        "--output-dir",
        output_dir,
    ]
    dry_run = command + ["--dry-run"]
    return shell_join(command), shell_join(dry_run)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n")


def write_candidate_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CANDIDATE_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column) for column in CANDIDATE_COLUMNS})


def write_planned_commands(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        "# HYDRA label-lab planned commands.",
        "# These are gauntlet dry-runs only. They do not execute validation.",
        "",
    ]
    for row in rows:
        if row.get("available"):
            lines.append(f"# {row['candidate']}")
            lines.append(str(row["dry_run_gauntlet_command"]))
            lines.append("")
        else:
            lines.append(f"# skipped {row['candidate']}: {row.get('unavailable_reason')}")
    path.write_text("\n".join(lines).rstrip() + "\n")


def md_value(value: Any, digits: int = 6) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def write_summary_md(path: Path, summary: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    lines = [
        "# HYDRA Label Design Lab Summary",
        "",
        "## Run metadata",
        "",
        f"- run_id: `{summary['run_id']}`",
        f"- started UTC: {summary['started_utc']}",
        f"- finished UTC: {summary['finished_utc']}",
        f"- source dataset: `{summary['dataset']}`",
        f"- source rows loaded: {summary['source_rows_loaded']}",
        f"- max rows: {summary['max_rows'] if summary['max_rows'] is not None else 'full'}",
        "",
        "## Safety",
        "",
        "- No files were written under data/.",
        "- No canonical dataset was rebuilt.",
        "- No training or gauntlet validation was run.",
        "- Planned gauntlet commands include --dry-run.",
        "",
        "## Candidates",
        "",
        "| candidate | available | label | return | horizon | rows | positive_rate | nan_rate | mismatch | dataset |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---|",
    ]

    for row in rows:
        lines.append(
            "| "
            f"{row.get('candidate')} | {row.get('available')} | {row.get('label_column')} | "
            f"{row.get('return_column')} | {row.get('horizon_bars')} | {row.get('row_count')} | "
            f"{md_value(row.get('positive_rate'), 4)} | {md_value(row.get('nan_rate'), 4)} | "
            f"{md_value(row.get('label_return_sign_mismatch'), 4)} | "
            f"{row.get('dataset_path') or row.get('unavailable_reason')} |"
        )

    lines.extend(
        [
            "",
            "## Planned gauntlet commands",
            "",
            f"- `{summary['planned_gauntlet_commands_path']}`",
            "",
            "## Recommendation",
            "",
            "Use these datasets only as label-design experiments. Run the gauntlet manually and require baseline-beating non-overlap evidence before making any alpha claim.",
        ]
    )
    path.write_text("\n".join(lines) + "\n")


def dry_run(args: argparse.Namespace, run_name: str, costs: list[float]) -> int:
    output_dir = validate_output_dir(args.output_dir)
    run_dir = output_dir / run_name
    dataset_dir = run_dir / "datasets"
    print("DRY_RUN: no files written and no parquet datasets created.")
    print(f"RUN_ID: {run_name}")
    print(f"SOURCE_DATASET: {args.dataset}")
    print(f"PLANNED_DATASET_DIR: {dataset_dir}")
    print("")
    for spec in candidate_specs(costs, include_20b=True):
        dataset_path = dataset_dir / f"{safe_name(spec.name)}.parquet"
        _, dry_command = gauntlet_commands(dataset_path, spec)
        condition = f" ({spec.conditional_reason})" if spec.conditional_reason else ""
        print(f"- {spec.name}: {spec.label_column} / {spec.return_column}{condition}")
        print(f"  {dry_command}")
    return 0


def build_lab(args: argparse.Namespace, run_name: str, costs: list[float]) -> int:
    output_dir = validate_output_dir(args.output_dir)
    run_dir = output_dir / run_name
    dataset_dir = run_dir / "datasets"
    candidate_dir = run_dir / "candidates"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    candidate_dir.mkdir(parents=True, exist_ok=True)

    started = utc_now()
    source_df = load_dataset(Path(args.dataset), args.max_rows)
    columns = set(source_df.columns)
    include_20b = "fwd_ret_20b" in columns
    rows: list[dict[str, Any]] = []

    for spec in candidate_specs(costs, include_20b=include_20b):
        dataset_path = dataset_dir / f"{safe_name(spec.name)}.parquet"
        metadata_path = candidate_dir / f"{safe_name(spec.name)}.json"
        recommended, dry_command = gauntlet_commands(dataset_path, spec)
        status, transform = transform_candidate(source_df, spec)

        row: dict[str, Any] = {
            "candidate": spec.name,
            "available": bool(status.get("available")),
            "unavailable_reason": status.get("unavailable_reason"),
            "dataset_path": str(dataset_path) if status.get("available") else None,
            "metadata_path": str(metadata_path),
            "label_column": spec.label_column,
            "return_column": spec.return_column,
            "horizon_bars": spec.horizon_bars,
            "cost_bps": spec.cost_bps,
            "recommended_gauntlet_command": recommended if status.get("available") else None,
            "dry_run_gauntlet_command": dry_command if status.get("available") else None,
        }

        if status.get("available"):
            derived = source_df.copy(deep=False)
            if spec.kind == "triple_barrier_aligned":
                derived[spec.return_column] = status["tb_ret"]
            elif transform is not None:
                derived[spec.label_column] = transform(source_df)
            else:
                row["available"] = False
                row["unavailable_reason"] = "candidate transform unavailable"

            if row["available"]:
                derived.to_parquet(dataset_path, index=False)
                row.update(summarize_candidate(derived, spec))
        else:
            row.update(
                {
                    "row_count": None,
                    "positive_rate": None,
                    "nan_rate": None,
                    "return_mean": None,
                    "return_std": None,
                    "return_min": None,
                    "return_max": None,
                    "label_return_sign_mismatch": None,
                }
            )

        metadata = {
            **row,
            "source_dataset": args.dataset,
            "source_rows_loaded": len(source_df),
            "max_rows": args.max_rows,
            "kind": spec.kind,
            "created_utc": utc_now(),
            "details": {key: value for key, value in status.items() if key not in {"tb_ret"}},
        }
        write_json(metadata_path, metadata)
        rows.append(row)

    finished = utc_now()
    planned_path = run_dir / "planned_gauntlet_commands.sh"
    write_candidate_csv(run_dir / "label_candidates.csv", rows)
    write_planned_commands(planned_path, rows)

    summary = {
        "run_id": run_name,
        "started_utc": started,
        "finished_utc": finished,
        "dataset": args.dataset,
        "output_dir": str(output_dir),
        "run_dir": str(run_dir),
        "dataset_dir": str(dataset_dir),
        "source_rows_loaded": len(source_df),
        "source_columns_loaded": len(source_df.columns),
        "max_rows": args.max_rows,
        "cost_bps_list": costs,
        "planned_gauntlet_commands_path": str(planned_path),
        "label_candidates_csv": str(run_dir / "label_candidates.csv"),
        "candidates": rows,
        "safety": {
            "data_dir_mutated": False,
            "gauntlet_run": False,
            "training_run": False,
            "alpha_claim": False,
        },
    }
    write_json(run_dir / "summary.json", summary)
    write_summary_md(run_dir / "summary.md", summary, rows)

    print(f"RUN_ID: {run_name}")
    print(f"SUMMARY_JSON: {run_dir / 'summary.json'}")
    print(f"SUMMARY_MD: {run_dir / 'summary.md'}")
    print(f"LABEL_CANDIDATES: {run_dir / 'label_candidates.csv'}")
    print(f"PLANNED_GAUNTLET_COMMANDS: {planned_path}")
    return 0


def main() -> int:
    args = parse_args()
    costs = parse_costs(args.cost_bps_list)
    name = run_id()
    if args.dry_run:
        return dry_run(args, name, costs)
    return build_lab(args, name, costs)


if __name__ == "__main__":
    raise SystemExit(main())
