#!/usr/bin/env python3
"""Agent-Prime system and dataset reconnaissance."""

from __future__ import annotations

import argparse
import csv
import glob
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq


TARGET_PREFIXES = ("fwd_ret", "label_", "future_", "target")
OHLC_NAMES = {"open", "high", "low", "close", "a_open", "a_high", "a_low", "a_close"}
TIME_CANDIDATES = ("time", "timestamp", "date", "datetime")


def git_output(args: list[str]) -> str:
    try:
        return subprocess.check_output(["git", *args], text=True, stderr=subprocess.STDOUT).strip()
    except Exception as exc:
        return f"ERROR: {exc}"


def package_status(name: str) -> dict:
    try:
        mod = importlib.import_module(name)
        return {"available": True, "version": getattr(mod, "__version__", "unknown")}
    except Exception as exc:
        return {"available": False, "error": f"{type(exc).__name__}: {exc}"}


def system_recon() -> dict:
    ram = {"available": False}
    try:
        import psutil

        vm = psutil.virtual_memory()
        ram = {
            "available": True,
            "total_gb": round(vm.total / 1024**3, 3),
            "available_gb": round(vm.available / 1024**3, 3),
        }
    except Exception as exc:
        ram = {"available": False, "error": f"{type(exc).__name__}: {exc}"}

    packages = {
        name: package_status(name)
        for name in [
            "pandas",
            "numpy",
            "scipy",
            "sklearn",
            "lightgbm",
            "xgboost",
            "catboost",
            "polars",
            "pyarrow",
            "QuantLib",
            "sklearnex",
            "torch",
        ]
    }

    gpu = {"torch_cuda_available": False}
    try:
        import torch

        gpu = {
            "torch_cuda_available": bool(torch.cuda.is_available()),
            "gpu_count": int(torch.cuda.device_count()) if torch.cuda.is_available() else 0,
            "gpu_name_0": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        }
    except Exception as exc:
        gpu = {"torch_cuda_available": False, "error": f"{type(exc).__name__}: {exc}"}

    return {
        "repo_root": git_output(["rev-parse", "--show-toplevel"]),
        "git_branch": git_output(["branch", "--show-current"]),
        "git_status_summary": git_output(["status", "--short", "--branch"]),
        "python_executable": sys.executable,
        "python_version": sys.version.replace("\n", " "),
        "cpu_count_logical": os.cpu_count(),
        "ram": ram,
        "gpu": gpu,
        "packages": packages,
    }


def normalize_columns(columns: pd.Index) -> list[str]:
    if isinstance(columns, pd.MultiIndex):
        return [
            "_".join(str(part).strip() for part in col if str(part).strip())
            for col in columns
        ]
    return [str(c) for c in columns]


def pick_time_col(columns: list[str]) -> str | None:
    lower = {c.lower(): c for c in columns}
    for candidate in TIME_CANDIDATES:
        if candidate in lower:
            return lower[candidate]
    return None


def target_cols(columns: list[str]) -> list[str]:
    out = []
    for col in columns:
        low = col.lower()
        if low.startswith(TARGET_PREFIXES) or "fwd_ret" in low:
            out.append(col)
    return out


def ohlc_cols(columns: list[str]) -> list[str]:
    out = []
    for col in columns:
        low = col.lower()
        if low in OHLC_NAMES or low.endswith("_open") or low.endswith("_high") or low.endswith("_low") or low.endswith("_close"):
            out.append(col)
    return out


def summarize_frame(path: Path, df: pd.DataFrame, file_size_mb: float) -> dict:
    df = df.copy()
    df.columns = normalize_columns(df.columns)
    columns = list(df.columns)
    time_col = pick_time_col(columns)
    targets = target_cols(columns)
    ohlc = ohlc_cols(columns)
    feature_count = len([c for c in columns if c != time_col and c not in targets])

    first_ts = None
    last_ts = None
    duplicate_ts = None
    if time_col is not None:
        ts = pd.to_datetime(df[time_col], utc=True, errors="coerce")
        first_ts = str(ts.min()) if ts.notna().any() else None
        last_ts = str(ts.max()) if ts.notna().any() else None
        duplicate_ts = int(ts.duplicated().sum())

    nan_pct = float(df.isna().to_numpy().mean() * 100.0) if len(df.columns) else 0.0
    memory_mb = float(df.memory_usage(deep=True).sum() / 1024**2)

    return {
        "path": str(path),
        "rows": int(len(df)),
        "columns": int(len(columns)),
        "file_size_mb": round(file_size_mb, 3),
        "memory_estimate_mb": round(memory_mb, 3),
        "first_timestamp": first_ts,
        "last_timestamp": last_ts,
        "target_columns": "|".join(targets),
        "ohlc_columns": "|".join(ohlc),
        "feature_count": int(feature_count),
        "nan_percentage": round(nan_pct, 6),
        "duplicate_timestamp_count": duplicate_ts,
        "error": "",
    }


def summarize_parquet(path: Path) -> dict:
    pf = pq.ParquetFile(path)
    meta = pf.metadata
    schema_cols = list(pf.schema_arrow.names)
    rows = int(meta.num_rows)
    cols = int(meta.num_columns)
    file_size_mb = path.stat().st_size / 1024**2

    targets = target_cols(schema_cols)
    ohlc = ohlc_cols(schema_cols)
    time_col = pick_time_col(schema_cols)

    first_ts = None
    last_ts = None
    duplicate_ts = None
    if time_col is not None:
        try:
            ts_df = pd.read_parquet(path, columns=[time_col])
            ts = pd.to_datetime(ts_df[time_col], utc=True, errors="coerce")
            first_ts = str(ts.min()) if ts.notna().any() else None
            last_ts = str(ts.max()) if ts.notna().any() else None
            duplicate_ts = int(ts.duplicated().sum())
        except Exception:
            first_ts = None
            last_ts = None
            duplicate_ts = None

    null_count = 0
    null_stats_complete = True
    for rg_idx in range(meta.num_row_groups):
        rg = meta.row_group(rg_idx)
        for col_idx in range(meta.num_columns):
            stats = rg.column(col_idx).statistics
            if stats is None or stats.null_count is None:
                null_stats_complete = False
                break
            null_count += int(stats.null_count)
        if not null_stats_complete:
            break

    if null_stats_complete and rows * cols > 0:
        nan_pct = float(null_count / (rows * cols) * 100.0)
        memory_mb = None
    else:
        # Fall back to a real read when metadata do not include null counts.
        # This preserves the requested NaN statistic without turning the normal
        # Parquet path into a full-load operation for thousands of files.
        df = pd.read_parquet(path)
        return summarize_frame(path, df, file_size_mb)

    return {
        "path": str(path),
        "rows": rows,
        "columns": cols,
        "file_size_mb": round(file_size_mb, 3),
        "memory_estimate_mb": memory_mb,
        "first_timestamp": first_ts,
        "last_timestamp": last_ts,
        "target_columns": "|".join(targets),
        "ohlc_columns": "|".join(ohlc),
        "feature_count": int(len([c for c in schema_cols if c != time_col and c not in targets])),
        "nan_percentage": round(nan_pct, 6),
        "duplicate_timestamp_count": duplicate_ts,
        "error": "",
    }


def summarize_csv(path: Path) -> dict:
    chunks = []
    for chunk in pd.read_csv(path, chunksize=100_000):
        chunks.append(chunk)
    df = pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame()
    return summarize_frame(path, df, path.stat().st_size / 1024**2)


def summarize_path(path: Path) -> dict:
    try:
        if path.suffix.lower() == ".parquet":
            return summarize_parquet(path)
        if path.suffix.lower() == ".csv":
            return summarize_csv(path)
        raise ValueError(f"unsupported extension: {path.suffix}")
    except Exception as exc:
        return {
            "path": str(path),
            "rows": None,
            "columns": None,
            "file_size_mb": round(path.stat().st_size / 1024**2, 3) if path.exists() else None,
            "memory_estimate_mb": None,
            "first_timestamp": None,
            "last_timestamp": None,
            "target_columns": "",
            "ohlc_columns": "",
            "feature_count": None,
            "nan_percentage": None,
            "duplicate_timestamp_count": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


def candidate_paths() -> list[Path]:
    paths: list[str] = []
    for pattern in ["data/**/*.parquet", "data/**/*.csv", "reports/**/*.parquet"]:
        paths.extend(glob.glob(pattern, recursive=True))
    return [Path(p) for p in sorted(set(paths))]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-json", default="reports/agent_prime_recon.json")
    parser.add_argument("--output-csv", default="reports/agent_prime_candidate_dataset_summary.csv")
    parser.add_argument("--max-candidates", type=int, default=None)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    paths = candidate_paths()
    if args.max_candidates is not None:
        paths = paths[: args.max_candidates]

    rows = []
    for i, path in enumerate(paths, 1):
        if not args.quiet:
            print(f"[{i}/{len(paths)}] {path}", flush=True)
        rows.append(summarize_path(path))

    out_json = Path(args.output_json)
    out_csv = Path(args.output_csv)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    report = {"system": system_recon(), "candidate_count": len(rows), "candidates": rows}
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["path"])
        writer.writeheader()
        writer.writerows(rows)

    print(json.dumps({"system": report["system"], "candidate_count": len(rows), "json": str(out_json), "csv": str(out_csv)}, indent=2))


if __name__ == "__main__":
    main()
