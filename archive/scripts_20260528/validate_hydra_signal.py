#!/usr/bin/env python3
"""
Strict walk-forward signal validation for HYDRA datasets.

This is a reusable research harness only. It reads a Parquet dataset, trains on
chronological expanding folds, evaluates strict baselines, and writes a report
under the selected output directory. It does not mutate datasets or tune on test
folds.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
import time
import threading
import warnings as _warnings
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Suppress sklearn feature-name UserWarning when passing NumPy arrays
_warnings.filterwarnings("ignore", message=".*does not have valid feature names.*", category=UserWarning)

# ─────────────────────────────────────────────────────────────────────────────
# Progress UI
# ─────────────────────────────────────────────────────────────────────────────

_RICH_AVAILABLE = False
try:
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn, MofNCompleteColumn
    from rich.console import Console
    from rich.table import Table
    _RICH_AVAILABLE = True
except ImportError:
    pass


class PlainProgress:
    """Fallback progress reporter when Rich is unavailable."""

    def __init__(self, total_folds: int, log_every: float = 30.0):
        self._total = total_folds
        self._log_every = log_every
        self._start = time.time()

    def start(self) -> None:
        print(f"[progress] Starting {self._total} folds...")

    def begin_fold(self, fold_num: int) -> None:
        elapsed = time.time() - self._start
        print(f"[fold {fold_num}/{self._total}] starting (elapsed {elapsed:.1f}s)")

    def update_phase(self, fold_num: int, phase: str) -> None:
        elapsed = time.time() - self._start
        print(f"[fold {fold_num}/{self._total}] {phase} (elapsed {elapsed:.1f}s)")

    def end_fold(self, fold_num: int, fold_time: float) -> None:
        elapsed = time.time() - self._start
        remaining = (elapsed / fold_num) * (self._total - fold_num) if fold_num > 0 else 0
        print(f"[fold {fold_num}/{self._total}] done in {fold_time:.1f}s (ETA {remaining:.0f}s)")

    def finish(self) -> None:
        elapsed = time.time() - self._start
        print(f"[progress] All folds complete in {elapsed:.1f}s")


class RichProgress:
    """Rich-based progress reporter."""

    def __init__(self, total_folds: int, log_every: float = 30.0):
        self._total = total_folds
        self._console = Console()
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=self._console,
        )
        self._task_id = None
        self._start = time.time()

    def start(self) -> None:
        self._progress.start()
        self._task_id = self._progress.add_task("Walk-forward folds", total=self._total)

    def begin_fold(self, fold_num: int) -> None:
        self._progress.update(self._task_id, description=f"Fold {fold_num}/{self._total}")

    def update_phase(self, fold_num: int, phase: str) -> None:
        self._progress.update(self._task_id, description=f"Fold {fold_num}/{self._total}: {phase}")

    def end_fold(self, fold_num: int, fold_time: float) -> None:
        self._progress.advance(self._task_id)
        self._progress.update(self._task_id, description=f"Fold {fold_num} done ({fold_time:.1f}s)")

    def finish(self) -> None:
        elapsed = time.time() - self._start
        self._progress.update(self._task_id, description=f"Complete ({elapsed:.1f}s)")
        self._progress.stop()


class NoProgress:
    """Silent progress (--no-progress)."""

    def start(self) -> None: pass
    def begin_fold(self, fold_num: int) -> None: pass
    def update_phase(self, fold_num: int, phase: str) -> None: pass
    def end_fold(self, fold_num: int, fold_time: float) -> None: pass
    def finish(self) -> None: pass


def make_progress(mode: str, total_folds: int, log_every: float) -> Any:
    """Create progress reporter based on mode."""
    if mode == "none":
        return NoProgress()
    if mode == "rich" or (mode == "auto" and _RICH_AVAILABLE):
        return RichProgress(total_folds, log_every)
    return PlainProgress(total_folds, log_every)


class FitHeartbeat:
    """Background heartbeat during slow model fitting."""

    def __init__(self, fold_num: int, interval: float = 30.0):
        self._fold = fold_num
        self._interval = interval
        self._start = time.time()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def __enter__(self) -> "FitHeartbeat":
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_: Any) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1.0)

    def _run(self) -> None:
        while not self._stop_event.wait(self._interval):
            elapsed = time.time() - self._start
            print(f"  [heartbeat] Fold {self._fold}: model fit running... elapsed {elapsed:.0f}s")


@dataclass
class FoldTiming:
    """Timing breakdown for a single fold."""
    preprocess_seconds: float = 0.0
    fit_seconds: float = 0.0
    predict_seconds: float = 0.0
    metric_seconds: float = 0.0
    fold_seconds: float = 0.0


DEFAULT_OUTPUT_DIR = "reports/signal_validation"
DEFAULT_MODEL = "lightgbm_or_sklearn_fallback"
TIME_COLUMN_CANDIDATES = (
    "time",
    "timestamp",
    "datetime",
    "date",
    "bar_time",
    "open_time",
    "close_time",
)
PRICE_COLUMN_CANDIDATES = (
    "close",
    "A_close",
    "xau_close",
    "XAUUSD_close",
    "bid_close",
    "mid_close",
)


@dataclass(frozen=True)
class Fold:
    number: int
    train_start: int
    train_end: int
    embargo_start: int
    embargo_end: int
    test_start: int
    test_end: int


@dataclass(frozen=True)
class ModelSpec:
    name: str
    backend: str
    model: Any


@dataclass(frozen=True)
class ReturnStream:
    column: str | None
    status: str
    reason: str
    series: Any
    pnl_enabled: bool
    source: str


class HelpFormatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawDescriptionHelpFormatter,
):
    """Keep CLI examples readable while retaining default values."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run strict chronological walk-forward signal validation for a HYDRA "
            "Parquet dataset. The harness fits preprocessing, feature selection, "
            "and the model on train folds only, applies an embargo before each "
            "test fold, compares against simple baselines when a separate return "
            "stream is available, and writes CSV/JSON/MD reports under a unique "
            "run directory."
        ),
        formatter_class=HelpFormatter,
        epilog=(
            "Examples:\n"
            "  python scripts/validate_hydra_signal.py --dataset data/hydra_xauusd_m5_master_clean.parquet "
            "--label-column label_72b --return-column fwd_ret_72b --folds 5 --embargo-bars 288 "
            "--output-dir reports/signal_validation_master_72b\n"
            "  python scripts/validate_hydra_signal.py --dataset data/hydra_xauusd_m5_master_clean.parquet "
            "--label-column label_288b --folds 5 --embargo-bars 288 "
            "--output-dir reports/signal_validation_master_288b_classification\n"
            "Not accepted as PnL streams by default: pct_ret_*, log_ret_*, or label_* columns."
        ),
    )
    parser.add_argument(
        "--dataset",
        required=True,
        help="Path to the HYDRA Parquet dataset to validate.",
    )
    parser.add_argument(
        "--label-column",
        "--label",
        dest="label_column",
        required=True,
        help=(
            "Classification target column. Binary 0/1 and -1/1 labels are "
            "converted safely; continuous labels are binarized as value > 0. "
            "--label is a backward-compatible alias. This column is not used "
            "for PnL."
        ),
    )
    parser.add_argument(
        "--return-column",
        default=None,
        help=(
            "Optional forward-return column used only for PnL and baseline "
            "return metrics. If omitted, the script tries safe mappings such "
            "as label_72b -> fwd_ret_72b only when that forward-return column "
            "exists. pct_ret_* and log_ret_* are historical return features and "
            "are not auto-used for PnL. Binary direction labels are rejected as "
            "return streams by default."
        ),
    )
    parser.add_argument(
        "--allow-binary-return-stream",
        action="store_true",
        help=(
            "Allow a 0/1 or -1/1 return-column candidate to be used for PnL. "
            "Default false because binary direction labels are not returns."
        ),
    )
    parser.add_argument(
        "--folds",
        type=int,
        default=5,
        help="Number of chronological expanding walk-forward folds.",
    )
    parser.add_argument(
        "--embargo-bars",
        type=int,
        default=288,
        help="Number of bars skipped between each train window and test window.",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help=(
            "Optional first-N row cap for manual smoke runs. Rows are never "
            "sampled randomly."
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help="Base directory where a run_id subdirectory will be written.",
    )
    parser.add_argument(
        "--cost-bps",
        type=float,
        default=2.0,
        help="Cost in basis points charged per unit of turnover.",
    )
    parser.add_argument(
        "--random-seeds",
        type=int,
        default=10,
        help="Number of deterministic random long/short baseline seeds.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        choices=[
            "lightgbm_or_sklearn_fallback",
            "lightgbm",
            "hist_gradient_boosting",
            "random_forest",
        ],
        help=(
            "Primary model. The default uses LightGBM when installed, otherwise "
            "falls back to a small sklearn classifier."
        ),
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Suppress all progress output (timings still recorded in outputs).",
    )
    parser.add_argument(
        "--progress-mode",
        choices=["auto", "rich", "plain"],
        default="auto",
        help="Progress display backend. 'auto' uses Rich if installed, else plain.",
    )
    parser.add_argument(
        "--log-every-seconds",
        type=float,
        default=30.0,
        help="Heartbeat interval (seconds) during long model fits.",
    )
    return parser.parse_args()


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(2)


def require_runtime_dependencies() -> tuple[Any, Any]:
    try:
        import numpy as np
        import pandas as pd
    except ImportError as exc:
        fail(f"missing required runtime dependency: {exc.name}")

    return np, pd


def load_dataset(dataset_path: Path, max_rows: int | None) -> Any:
    _, pd = require_runtime_dependencies()

    if not dataset_path.exists():
        fail(f"dataset not found: {dataset_path}")
    if not dataset_path.is_file():
        fail(f"dataset path is not a file: {dataset_path}")

    df = pd.read_parquet(dataset_path)
    if max_rows is not None:
        if max_rows <= 0:
            fail("--max-rows must be positive when provided")
        df = df.iloc[:max_rows].copy()

    if df.empty:
        fail("dataset has zero rows after applying --max-rows")

    return df


def find_time_column(columns: list[str]) -> str | None:
    lower_to_actual = {col.lower(): col for col in columns}
    for candidate in TIME_COLUMN_CANDIDATES:
        if candidate.lower() in lower_to_actual:
            return lower_to_actual[candidate.lower()]
    return None


def find_price_column(columns: list[str]) -> str | None:
    lower_to_actual = {col.lower(): col for col in columns}
    for candidate in PRICE_COLUMN_CANDIDATES:
        if candidate.lower() in lower_to_actual:
            return lower_to_actual[candidate.lower()]
    return None


def validate_chronology(df: Any, time_col: str | None) -> dict[str, Any]:
    if time_col is None:
        return {
            "time_column": None,
            "split_basis": "row_order_no_time_column",
            "time_monotonic": None,
        }

    series = df[time_col]
    if series.isna().any():
        fail(f"time column has null values: {time_col}")
    if not series.is_monotonic_increasing:
        fail(
            f"time column is not monotonic increasing: {time_col}; "
            "refusing non-chronological validation"
        )

    duplicated = bool(series.duplicated().any())
    return {
        "time_column": time_col,
        "split_basis": "monotonic_time_column",
        "time_monotonic": True,
        "time_duplicates": duplicated,
        "time_min": str(series.iloc[0]),
        "time_max": str(series.iloc[-1]),
    }


def is_time_like_column(name: str) -> bool:
    lower = name.lower()
    if lower in {candidate.lower() for candidate in TIME_COLUMN_CANDIDATES}:
        return True
    return lower.endswith(("_time", "_timestamp", "_datetime", "_date"))


def is_label_or_forward_column(name: str, selected_label: str) -> bool:
    lower = name.lower()
    selected = selected_label.lower()

    if lower == selected:
        return True

    if lower.startswith(("label", "target", "y_", "z4_")):
        return True

    if "__label__" in lower or "_label_" in lower:
        return True

    forward_patterns = (
        "fwd",
        "forward",
        "future",
        "next_",
        "_next",
        "lead_",
        "_lead",
        "lookahead",
    )
    return any(pattern in lower for pattern in forward_patterns)


def numeric_feature_columns(df: Any, selected_label: str) -> tuple[list[str], dict[str, int]]:
    _, pd = require_runtime_dependencies()

    excluded = {
        "selected_label": 0,
        "label_or_forward": 0,
        "time_like": 0,
        "non_numeric": 0,
    }
    feature_cols: list[str] = []

    for col in df.columns:
        if col == selected_label:
            excluded["selected_label"] += 1
            continue
        if is_label_or_forward_column(col, selected_label):
            excluded["label_or_forward"] += 1
            continue
        if is_time_like_column(col):
            excluded["time_like"] += 1
            continue
        if not pd.api.types.is_numeric_dtype(df[col]):
            excluded["non_numeric"] += 1
            continue
        feature_cols.append(col)

    if not feature_cols:
        fail("no numeric feature columns remain after leakage exclusions")

    return feature_cols, excluded


def binary_domain(values: Any) -> str | None:
    np, _ = require_runtime_dependencies()

    unique = np.unique(np.asarray(values, dtype=float))
    unique = unique[np.isfinite(unique)]
    if len(unique) == 0:
        return None

    is_zero_one = all(
        any(np.isclose(value, allowed) for allowed in (0.0, 1.0))
        for value in unique
    )
    if is_zero_one:
        return "0/1"

    is_minus_one_one = all(
        any(np.isclose(value, allowed) for allowed in (-1.0, 1.0))
        for value in unique
    )
    if is_minus_one_one:
        return "-1/1"

    return None


def prepare_label(df: Any, label_col: str) -> tuple[Any, Any, Any, str]:
    _, pd = require_runtime_dependencies()

    if label_col not in df.columns:
        available_hint = ", ".join(list(map(str, df.columns[:12])))
        fail(
            f"label column missing: {label_col}. First available columns: "
            f"{available_hint}"
        )

    label = pd.to_numeric(df[label_col], errors="coerce")
    valid_mask = label.notna()
    if not bool(valid_mask.any()):
        fail(f"label column has no numeric non-null values: {label_col}")

    df_valid = df.loc[valid_mask].reset_index(drop=True)
    label_values = label.loc[valid_mask].astype(float).reset_index(drop=True)
    domain = binary_domain(label_values.to_numpy())

    if domain == "0/1":
        y = (label_values > 0.5).astype(int)
        label_mode = "binary_01"
    elif domain == "-1/1":
        y = (label_values > 0.0).astype(int)
        label_mode = "binary_pm1"
    else:
        y = (label_values > 0.0).astype(int)
        label_mode = "continuous_sign"

    if int(y.nunique()) < 2:
        fail(f"label column has only one class after binarization: {label_col}")

    return df_valid, y.reset_index(drop=True), label_values, label_mode


def return_candidates_from_label(label_col: str, columns: list[str]) -> list[str]:
    lower_to_actual = {col.lower(): col for col in columns}
    label_lower = label_col.lower()
    candidates: list[str] = []

    def add(candidate: str) -> None:
        actual = lower_to_actual.get(candidate.lower())
        if actual is not None and actual not in candidates:
            candidates.append(actual)

    match = re.fullmatch(r"label_(\d+b)", label_lower)
    if match:
        add(f"fwd_ret_{match.group(1)}")

    return candidates


def resolve_return_stream(
    df: Any,
    label_col: str,
    requested_return_col: str | None,
    allow_binary_return_stream: bool,
) -> ReturnStream:
    _, pd = require_runtime_dependencies()

    if requested_return_col:
        if requested_return_col not in df.columns:
            fail(f"return column missing: {requested_return_col}")
        if not pd.api.types.is_numeric_dtype(df[requested_return_col]):
            fail(f"return column must be numeric: {requested_return_col}")
        candidate = requested_return_col
        source = "requested"
    else:
        candidates = return_candidates_from_label(label_col, list(df.columns))
        candidate = candidates[0] if candidates else None
        source = "auto_detected" if candidate is not None else "not_found"

    if candidate is None:
        return ReturnStream(
            column=None,
            status="MISSING",
            reason=(
                "No separate return stream was provided or safely auto-detected; "
                "PnL and baseline return metrics are disabled."
            ),
            series=None,
            pnl_enabled=False,
            source=source,
        )

    series = pd.to_numeric(df[candidate], errors="coerce").astype(float)
    if not bool(series.notna().any()):
        if requested_return_col:
            fail(f"return column has no numeric non-null values: {candidate}")
        return ReturnStream(
            column=candidate,
            status="MISSING",
            reason=f"Return candidate {candidate} has no numeric non-null values.",
            series=None,
            pnl_enabled=False,
            source=source,
        )

    domain = binary_domain(series.dropna().to_numpy())
    if domain is not None and not allow_binary_return_stream:
        reason = (
            f"Return candidate {candidate} has binary domain {domain}; refusing "
            "to use a direction label as a PnL return stream."
        )
        if requested_return_col:
            fail(reason)
        return ReturnStream(
            column=candidate,
            status="MISSING",
            reason=reason,
            series=None,
            pnl_enabled=False,
            source=source,
        )

    return ReturnStream(
        column=candidate,
        status="VALID",
        reason="Return stream accepted for PnL and baseline return metrics.",
        series=series.reset_index(drop=True),
        pnl_enabled=True,
        source=source,
    )


def make_walk_forward_folds(n_rows: int, folds: int, embargo_bars: int) -> list[Fold]:
    if folds <= 0:
        fail("--folds must be positive")
    if embargo_bars < 0:
        fail("--embargo-bars cannot be negative")

    fold_size = n_rows // (folds + 1)
    if fold_size <= 0:
        fail(
            f"not enough rows ({n_rows}) to create {folds} chronological folds"
        )

    results: list[Fold] = []
    for idx in range(folds):
        train_start = 0
        train_end = fold_size * (idx + 1)
        embargo_start = train_end
        embargo_end = min(embargo_start + embargo_bars, n_rows)
        test_start = embargo_end
        target_test_end = fold_size * (idx + 2) + embargo_bars
        test_end = min(target_test_end, n_rows)

        if train_end <= train_start:
            fail(f"fold {idx + 1} has empty train window")
        if test_end <= test_start:
            fail(
                f"fold {idx + 1} has empty test window after embargo; "
                "reduce --folds or --embargo-bars"
            )

        results.append(
            Fold(
                number=idx + 1,
                train_start=train_start,
                train_end=train_end,
                embargo_start=embargo_start,
                embargo_end=embargo_end,
                test_start=test_start,
                test_end=test_end,
            )
        )

    return results


def replace_nonfinite_with_nan(values: Any) -> Any:
    np, _ = require_runtime_dependencies()
    values = values.astype(float, copy=False)
    values[~np.isfinite(values)] = np.nan
    return values


def fit_train_only_transform(
    X_train: Any,
    X_test: Any,
    feature_names: list[str],
) -> tuple[Any, Any, list[str]]:
    np, _ = require_runtime_dependencies()

    try:
        from sklearn.feature_selection import VarianceThreshold
        from sklearn.impute import SimpleImputer
        from sklearn.preprocessing import RobustScaler
    except ImportError as exc:
        fail(f"missing sklearn dependency for preprocessing: {exc.name}")

    X_train = X_train.replace([np.inf, -np.inf], np.nan)
    X_test = X_test.replace([np.inf, -np.inf], np.nan)

    coverage = X_train.notna().mean(axis=0)
    kept_names = [name for name in feature_names if coverage.get(name, 0.0) >= 0.05]
    if not kept_names:
        fail("all features have less than 5 percent non-null coverage in train fold")

    X_train_raw = X_train[kept_names].to_numpy(dtype=float, copy=True)
    X_test_raw = X_test[kept_names].to_numpy(dtype=float, copy=True)
    X_train_raw = replace_nonfinite_with_nan(X_train_raw)
    X_test_raw = replace_nonfinite_with_nan(X_test_raw)

    imputer = SimpleImputer(strategy="median")
    scaler = RobustScaler(with_centering=True, with_scaling=True)
    selector = VarianceThreshold(threshold=0.0)

    X_train_imp = imputer.fit_transform(X_train_raw)
    X_test_imp = imputer.transform(X_test_raw)

    X_train_scaled = scaler.fit_transform(X_train_imp)
    X_test_scaled = scaler.transform(X_test_imp)

    X_train_selected = selector.fit_transform(X_train_scaled)
    X_test_selected = selector.transform(X_test_scaled)

    support = selector.get_support()
    selected_names = [name for name, keep in zip(kept_names, support) if keep]
    if not selected_names:
        fail("train-only variance selector removed every feature")

    return X_train_selected, X_test_selected, selected_names


def make_model(model_name: str, seed: int) -> ModelSpec:
    if model_name in {"lightgbm", "lightgbm_or_sklearn_fallback"}:
        try:
            from lightgbm import LGBMClassifier

            model = LGBMClassifier(
                objective="binary",
                n_estimators=200,
                learning_rate=0.05,
                num_leaves=31,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=seed,
                n_jobs=-1,
                verbose=-1,
            )
            return ModelSpec("lightgbm", "lightgbm", model)
        except ImportError:
            if model_name == "lightgbm":
                fail("LightGBM requested but not installed")

    if model_name in {"hist_gradient_boosting", "lightgbm_or_sklearn_fallback"}:
        try:
            from sklearn.ensemble import HistGradientBoostingClassifier

            model = HistGradientBoostingClassifier(
                max_iter=200,
                learning_rate=0.05,
                max_leaf_nodes=31,
                l2_regularization=1.0,
                random_state=seed,
            )
            return ModelSpec(
                "hist_gradient_boosting",
                "sklearn",
                model,
            )
        except ImportError:
            if model_name == "hist_gradient_boosting":
                fail("HistGradientBoostingClassifier is unavailable")

    try:
        from sklearn.ensemble import RandomForestClassifier
    except ImportError as exc:
        fail(f"missing sklearn fallback model dependency: {exc.name}")

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=10,
        min_samples_leaf=25,
        class_weight="balanced_subsample",
        random_state=seed,
        n_jobs=-1,
    )
    return ModelSpec("random_forest", "sklearn", model)


def probability_positive(model: Any, X_test: Any) -> Any:
    np, _ = require_runtime_dependencies()

    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(X_test)
        if proba.shape[1] == 1:
            only_class = int(getattr(model, "classes_", [0])[0])
            return np.ones(len(X_test)) if only_class == 1 else np.zeros(len(X_test))
        classes = list(model.classes_)
        positive_index = classes.index(1) if 1 in classes else -1
        return proba[:, positive_index]

    if hasattr(model, "decision_function"):
        scores = model.decision_function(X_test)
        return 1.0 / (1.0 + np.exp(-scores))

    predictions = model.predict(X_test)
    return np.asarray(predictions, dtype=float)


def classification_metrics(y_true: Any, y_pred: Any, y_proba: Any) -> dict[str, float | None]:
    np, _ = require_runtime_dependencies()

    try:
        from sklearn.metrics import (
            balanced_accuracy_score,
            precision_score,
            recall_score,
            roc_auc_score,
        )
    except ImportError as exc:
        fail(f"missing sklearn metrics dependency: {exc.name}")

    metrics: dict[str, float | None] = {
        "auc": None,
        "balanced_accuracy": None,
        "precision": None,
        "recall": None,
    }

    if len(np.unique(y_true)) >= 2:
        metrics["auc"] = float(roc_auc_score(y_true, y_proba))
    metrics["balanced_accuracy"] = float(balanced_accuracy_score(y_true, y_pred))
    metrics["precision"] = float(precision_score(y_true, y_pred, zero_division=0))
    metrics["recall"] = float(recall_score(y_true, y_pred, zero_division=0))
    return metrics


def strategy_return_after_cost(
    positions: Any,
    forward_returns: Any,
    cost_bps: float,
) -> dict[str, float | int]:
    np, _ = require_runtime_dependencies()

    pos = np.asarray(positions, dtype=float)
    rets = np.asarray(forward_returns, dtype=float)
    if len(pos) != len(rets):
        raise ValueError("positions and forward returns must have the same length")

    pos = np.nan_to_num(pos, nan=0.0, posinf=0.0, neginf=0.0)
    rets = np.nan_to_num(rets, nan=0.0, posinf=0.0, neginf=0.0)

    gross = float(np.sum(pos * rets))
    previous = np.concatenate(([0.0], pos[:-1]))
    deltas = np.abs(pos - previous)
    trades = int(np.count_nonzero(deltas > 0.0))
    turnover = float(np.sum(deltas))
    cost = turnover * (cost_bps / 10000.0)
    net = gross - cost

    return {
        "return_gross": gross,
        "return_after_cost": net,
        "cost": float(cost),
        "trades": trades,
        "turnover": turnover,
        "mean_position_abs": float(np.mean(np.abs(pos))) if len(pos) else 0.0,
    }


def build_momentum_positions(df: Any, price_col: str | None, lookback: int = 12) -> Any:
    np, pd = require_runtime_dependencies()

    if price_col is None:
        return np.zeros(len(df), dtype=float)

    close = pd.to_numeric(df[price_col], errors="coerce")
    delta = close - close.shift(lookback)
    positions = np.where(delta > 0.0, 1.0, np.where(delta < 0.0, -1.0, 0.0))
    positions[:lookback] = 0.0
    return positions.astype(float)


def baseline_returns(
    fold: Fold,
    df: Any,
    forward_returns: Any,
    model_positions: Any,
    cost_bps: float,
    random_seed_count: int,
    price_col: str | None,
) -> dict[str, Any]:
    np, _ = require_runtime_dependencies()

    test_returns = forward_returns.iloc[fold.test_start:fold.test_end].to_numpy()
    test_len = len(test_returns)

    baselines: dict[str, Any] = {
        "always_long": strategy_return_after_cost(
            np.ones(test_len, dtype=float),
            test_returns,
            cost_bps,
        ),
        "always_short": strategy_return_after_cost(
            np.full(test_len, -1.0, dtype=float),
            test_returns,
            cost_bps,
        ),
        "flat": strategy_return_after_cost(
            np.zeros(test_len, dtype=float),
            test_returns,
            cost_bps,
        ),
        "inverted_model": strategy_return_after_cost(
            -np.asarray(model_positions, dtype=float),
            test_returns,
            cost_bps,
        ),
    }

    full_momentum = build_momentum_positions(df, price_col)
    baselines["simple_momentum"] = strategy_return_after_cost(
        full_momentum[fold.test_start:fold.test_end],
        test_returns,
        cost_bps,
    )

    random_returns: list[float] = []
    random_turnovers: list[float] = []
    random_seed_count = max(0, random_seed_count)
    for seed_idx in range(random_seed_count):
        seed = 1009 * fold.number + seed_idx
        rng = np.random.default_rng(seed)
        positions = rng.choice([-1.0, 1.0], size=test_len)
        random_result = strategy_return_after_cost(positions, test_returns, cost_bps)
        random_returns.append(float(random_result["return_after_cost"]))
        random_turnovers.append(float(random_result["turnover"]))

    if random_returns:
        baselines["random_long_short_mean"] = {
            "return_after_cost": float(np.mean(random_returns)),
            "return_after_cost_best_seed": float(np.max(random_returns)),
            "return_after_cost_worst_seed": float(np.min(random_returns)),
            "return_after_cost_std": float(np.std(random_returns)),
            "turnover": float(np.mean(random_turnovers)),
            "trades": None,
            "seed_count": random_seed_count,
        }
        baselines["random_long_short_best_seed"] = {
            "return_after_cost": float(np.max(random_returns)),
            "turnover": None,
            "trades": None,
            "seed_count": random_seed_count,
        }
    else:
        baselines["random_long_short_mean"] = {
            "return_after_cost": None,
            "return_after_cost_best_seed": None,
            "return_after_cost_worst_seed": None,
            "return_after_cost_std": None,
            "turnover": None,
            "trades": None,
            "seed_count": 0,
        }
        baselines["random_long_short_best_seed"] = {
            "return_after_cost": None,
            "turnover": None,
            "trades": None,
            "seed_count": 0,
        }

    return baselines


def null_return_metrics() -> dict[str, None]:
    return {
        "return_gross": None,
        "return_after_cost": None,
        "cost": None,
        "trades": None,
        "turnover": None,
        "mean_position_abs": None,
    }


def null_baseline_returns() -> dict[str, dict[str, None]]:
    return {
        "always_long": null_return_metrics(),
        "always_short": null_return_metrics(),
        "flat": null_return_metrics(),
        "simple_momentum": null_return_metrics(),
        "inverted_model": null_return_metrics(),
        "random_long_short_mean": {
            "return_after_cost": None,
            "return_after_cost_best_seed": None,
            "return_after_cost_worst_seed": None,
            "return_after_cost_std": None,
            "turnover": None,
            "trades": None,
            "seed_count": None,
        },
        "random_long_short_best_seed": {
            "return_after_cost": None,
            "turnover": None,
            "trades": None,
            "seed_count": None,
        },
    }


def add_baseline_columns(row: dict[str, Any], baselines: dict[str, Any]) -> None:
    for baseline_name, result in baselines.items():
        prefix = f"baseline_{baseline_name}"
        for metric_name, metric_value in result.items():
            row[f"{prefix}_{metric_name}"] = metric_value


def best_baseline(baselines: dict[str, Any]) -> tuple[str | None, float | None]:
    best_name: str | None = None
    best_value: float | None = None
    for name, result in baselines.items():
        value = result.get("return_after_cost")
        if value is None:
            continue
        value = float(value)
        if best_value is None or value > best_value:
            best_name = name
            best_value = value
    return best_name, best_value


def finite_mean(values: list[float | None]) -> float | None:
    np, _ = require_runtime_dependencies()
    clean = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    if not clean:
        return None
    return float(np.mean(clean))


def finite_std(values: list[float | None]) -> float | None:
    np, _ = require_runtime_dependencies()
    clean = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    if not clean:
        return None
    return float(np.std(clean))


def rate(predicate_values: list[bool]) -> float:
    if not predicate_values:
        return 0.0
    return sum(1 for value in predicate_values if value) / len(predicate_values)


def build_warnings(label_col: str) -> list[str]:
    warnings = [
        "pct_ret_* and log_ret_* columns are historical return features and are not accepted as PnL streams by default.",
    ]
    if re.fullmatch(r"(?i)z4_\d{4}", label_col):
        warnings.append(
            "Z4 registry label selected without semantic mapping; use this target only after resolving registry metadata."
        )
    return warnings


def verdict_from_summary(summary: dict[str, Any]) -> tuple[str, str]:
    aggregates = summary["aggregates"]
    stability = summary["stability"]

    valid_folds = int(summary["folds"]["valid_folds"])
    requested_folds = int(summary["folds"]["requested_folds"])
    if valid_folds < requested_folds:
        return "SIGNAL_FAIL", "not every requested fold produced valid metrics"

    mean_auc = aggregates.get("mean_auc")
    mean_bal = aggregates.get("mean_balanced_accuracy")
    mean_return = aggregates.get("mean_model_return_after_cost")
    mean_excess = aggregates.get("mean_excess_over_best_baseline")

    if mean_auc is None or mean_bal is None:
        return "SIGNAL_FAIL", "core classification metrics were unavailable"

    if mean_auc <= 0.5 and mean_bal <= 0.5:
        return "SIGNAL_FAIL", "classification metrics did not beat chance"

    if not summary["return_stream"]["pnl_enabled"]:
        return (
            "CLASSIFICATION_ONLY_NO_PNL",
            "classification-only: no valid forward return stream",
        )

    if mean_return is None or mean_excess is None:
        return "SIGNAL_FAIL", "PnL metrics were unavailable despite return stream being enabled"

    if mean_excess <= 0.0 or stability["baseline_beaten_fold_rate"] < 0.5:
        return "BASELINE_DOMINATED", "model did not consistently beat baselines after cost"

    strict_candidate = (
        mean_auc >= 0.53
        and mean_bal >= 0.52
        and mean_return > 0.0
        and mean_excess > 0.0
        and stability["auc_above_50_fold_rate"] >= 0.8
        and stability["positive_return_fold_rate"] >= 0.6
        and stability["baseline_beaten_fold_rate"] >= 0.8
    )
    if strict_candidate:
        return "RESEARCH_CANDIDATE", "strict out-of-sample thresholds were met"

    return "WEAK_EDGE", "model beat baselines but failed strict research thresholds"


def make_run_id(dataset_path: Path, label_col: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dataset_slug = "".join(
        ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in dataset_path.stem
    )[:80]
    label_slug = "".join(
        ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in label_col
    )[:80]
    return f"{timestamp}_{dataset_slug}_{label_slug}"


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        if isinstance(value, float) and not math.isfinite(value):
            return None
        return value
    if hasattr(value, "item"):
        try:
            return json_safe(value.item())
        except Exception:
            return str(value)
    return str(value)


def run_validation(args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    np, _ = require_runtime_dependencies()

    run_start_time = time.time()

    dataset_path = Path(args.dataset)
    df = load_dataset(dataset_path, args.max_rows)

    if args.random_seeds < 0:
        fail("--random-seeds cannot be negative")
    if args.cost_bps < 0:
        fail("--cost-bps cannot be negative")

    time_col = find_time_column(list(df.columns))
    chronology = validate_chronology(df, time_col)

    df, y, label_values, label_mode = prepare_label(df, args.label_column)
    return_stream = resolve_return_stream(
        df,
        args.label_column,
        args.return_column,
        args.allow_binary_return_stream,
    )
    feature_cols, exclusions = numeric_feature_columns(df, args.label_column)
    price_col = find_price_column(list(df.columns))
    folds = make_walk_forward_folds(len(df), args.folds, args.embargo_bars)

    # Progress setup
    progress_mode = "none" if getattr(args, "no_progress", False) else getattr(args, "progress_mode", "auto")
    log_every = getattr(args, "log_every_seconds", 30.0)
    progress = make_progress(progress_mode, len(folds), log_every)

    # Run start banner
    print("=" * 70)
    print("HYDRA SIGNAL VALIDATION — Walk-Forward Harness")
    print("=" * 70)
    print(f"  Dataset:    {dataset_path}")
    print(f"  Rows:       {len(df):,}")
    print(f"  Features:   {len(feature_cols):,} candidates")
    print(f"  Label:      {args.label_column}")
    print(f"  Folds:      {args.folds}")
    print(f"  Embargo:    {args.embargo_bars} bars")
    print(f"  Model:      {args.model}")
    print(f"  Started:    {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 70)

    progress.start()

    rows: list[dict[str, Any]] = []
    for fold in folds:
        fold_start_time = time.time()
        timing = FoldTiming()
        progress.begin_fold(fold.number)

        train_slice = slice(fold.train_start, fold.train_end)
        test_slice = slice(fold.test_start, fold.test_end)

        y_train = y.iloc[train_slice].to_numpy()
        y_test = y.iloc[test_slice].to_numpy()
        if len(np.unique(y_train)) < 2 or len(np.unique(y_test)) < 2:
            timing.fold_seconds = time.time() - fold_start_time
            row = {
                "fold": fold.number,
                "fold_status": "SKIPPED_ONE_CLASS",
                "label_column": args.label_column,
                "return_column": return_stream.column,
                "return_stream_status": return_stream.status,
                "pnl_enabled": return_stream.pnl_enabled,
                "train_rows": fold.train_end - fold.train_start,
                "test_rows": fold.test_end - fold.test_start,
                "feature_count_candidates": len(feature_cols),
                "feature_count_used": 0,
                "auc": None,
                "balanced_accuracy": None,
                "precision": None,
                "recall": None,
                "fold_return_gross": None,
                "fold_return_after_cost": None,
                "fold_cost": None,
                "trades": None,
                "turnover_proxy": None,
                "best_baseline_name": None,
                "best_baseline_return_after_cost": None,
                "excess_over_best_baseline": None,
                "preprocess_seconds": timing.preprocess_seconds,
                "fit_seconds": timing.fit_seconds,
                "predict_seconds": timing.predict_seconds,
                "metric_seconds": timing.metric_seconds,
                "fold_seconds": timing.fold_seconds,
            }
            add_baseline_columns(row, null_baseline_returns())
            rows.append(row)
            progress.end_fold(fold.number, timing.fold_seconds)
            continue

        # Preprocess phase
        progress.update_phase(fold.number, "preprocess")
        t0 = time.time()
        X_train = df.iloc[train_slice][feature_cols]
        X_test = df.iloc[test_slice][feature_cols]
        X_train_selected, X_test_selected, selected_features = fit_train_only_transform(
            X_train,
            X_test,
            feature_cols,
        )
        timing.preprocess_seconds = time.time() - t0

        # Fit phase
        progress.update_phase(fold.number, "fit")
        t0 = time.time()
        model_spec = make_model(args.model, seed=42)
        with FitHeartbeat(fold.number, interval=log_every):
            model_spec.model.fit(X_train_selected, y_train)
        timing.fit_seconds = time.time() - t0

        # Predict phase
        progress.update_phase(fold.number, "predict")
        t0 = time.time()
        y_proba = probability_positive(model_spec.model, X_test_selected)
        y_pred = (y_proba >= 0.5).astype(int)
        positions = np.where(y_pred == 1, 1.0, -1.0)
        timing.predict_seconds = time.time() - t0

        # Metrics phase
        progress.update_phase(fold.number, "metrics")
        t0 = time.time()
        cls = classification_metrics(y_test, y_pred, y_proba)
        if return_stream.pnl_enabled:
            model_returns = strategy_return_after_cost(
                positions,
                return_stream.series.iloc[test_slice].to_numpy(),
                args.cost_bps,
            )
            baselines = baseline_returns(
                fold,
                df,
                return_stream.series,
                positions,
                args.cost_bps,
                args.random_seeds,
                price_col,
            )
        else:
            model_returns = null_return_metrics()
            baselines = null_baseline_returns()
        timing.metric_seconds = time.time() - t0

        timing.fold_seconds = time.time() - fold_start_time

        best_name, best_value = best_baseline(baselines)
        model_net = model_returns["return_after_cost"]
        excess = (
            float(model_net) - best_value
            if model_net is not None and best_value is not None
            else None
        )

        row: dict[str, Any] = {
            "fold": fold.number,
            "fold_status": "VALID",
            "label_column": args.label_column,
            "return_column": return_stream.column,
            "return_stream_status": return_stream.status,
            "pnl_enabled": return_stream.pnl_enabled,
            "train_start": fold.train_start,
            "train_end_exclusive": fold.train_end,
            "embargo_start": fold.embargo_start,
            "embargo_end_exclusive": fold.embargo_end,
            "test_start": fold.test_start,
            "test_end_exclusive": fold.test_end,
            "train_rows": fold.train_end - fold.train_start,
            "test_rows": fold.test_end - fold.test_start,
            "model": model_spec.name,
            "model_backend": model_spec.backend,
            "decision_threshold": 0.5,
            "feature_count_candidates": len(feature_cols),
            "feature_count_used": len(selected_features),
            "auc": cls["auc"],
            "balanced_accuracy": cls["balanced_accuracy"],
            "precision": cls["precision"],
            "recall": cls["recall"],
            "positive_label_rate_test": float(np.mean(y_test)),
            "positive_prediction_rate": float(np.mean(y_pred)),
            "fold_return_gross": model_returns["return_gross"],
            "fold_return_after_cost": model_returns["return_after_cost"],
            "fold_cost": model_returns["cost"],
            "trades": model_returns["trades"],
            "turnover_proxy": model_returns["turnover"],
            "best_baseline_name": best_name,
            "best_baseline_return_after_cost": best_value,
            "excess_over_best_baseline": excess,
            "preprocess_seconds": timing.preprocess_seconds,
            "fit_seconds": timing.fit_seconds,
            "predict_seconds": timing.predict_seconds,
            "metric_seconds": timing.metric_seconds,
            "fold_seconds": timing.fold_seconds,
        }

        add_baseline_columns(row, baselines)

        rows.append(row)

        # Live fold summary
        progress.end_fold(fold.number, timing.fold_seconds)
        auc_str = f"{cls['auc']:.4f}" if cls.get("auc") is not None else "N/A"
        print(
            f"  Fold {fold.number}: AUC={auc_str} | "
            f"preprocess={timing.preprocess_seconds:.1f}s fit={timing.fit_seconds:.1f}s "
            f"predict={timing.predict_seconds:.1f}s metrics={timing.metric_seconds:.1f}s "
            f"total={timing.fold_seconds:.1f}s"
        )

    progress.finish()
    total_runtime = time.time() - run_start_time
    print(f"\nTotal runtime: {total_runtime:.1f}s")

    valid_rows = [row for row in rows if row.get("fold_status") == "VALID"]
    aucs = [row.get("auc") for row in valid_rows]
    balanced = [row.get("balanced_accuracy") for row in valid_rows]
    returns = [row.get("fold_return_after_cost") for row in valid_rows]
    excesses = [row.get("excess_over_best_baseline") for row in valid_rows]
    feature_counts = [row.get("feature_count_used") for row in valid_rows]

    stability = {
        "auc_above_50_fold_rate": rate(
            [float(row["auc"]) > 0.5 for row in valid_rows if row.get("auc") is not None]
        ),
        "positive_return_fold_rate": (
            rate([float(row["fold_return_after_cost"]) > 0.0 for row in valid_rows])
            if return_stream.pnl_enabled
            else None
        ),
        "baseline_beaten_fold_rate": (
            rate(
                [
                    float(row["excess_over_best_baseline"]) > 0.0
                    for row in valid_rows
                    if row.get("excess_over_best_baseline") is not None
                ]
            )
            if return_stream.pnl_enabled
            else None
        ),
        "return_after_cost_std": finite_std(returns),
        "excess_over_baseline_std": finite_std(excesses),
    }

    summary: dict[str, Any] = {
        "run_id": make_run_id(dataset_path, args.label_column),
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "total_runtime_seconds": round(total_runtime, 2),
        "warnings": build_warnings(args.label_column),
        "config": {
            "dataset": str(dataset_path),
            "label": args.label_column,
            "label_column": args.label_column,
            "return_column": args.return_column,
            "folds": args.folds,
            "embargo_bars": args.embargo_bars,
            "max_rows": args.max_rows,
            "output_dir": args.output_dir,
            "cost_bps": args.cost_bps,
            "random_seeds": args.random_seeds,
            "model": args.model,
            "allow_binary_return_stream": args.allow_binary_return_stream,
            "threshold_policy": "fixed_0.5_no_test_tuning",
            "momentum_baseline_lookback_bars": 12,
        },
        "dataset": {
            "rows_after_label_drop": len(df),
            "columns": len(df.columns),
            "chronology": chronology,
            "price_column_for_momentum": price_col,
            "label_column": args.label_column,
            "label_mode": label_mode,
            "label_positive_rate": float(y.mean()),
            "label_abs_median": float(label_values.abs().median()),
            "label_abs_max": float(label_values.abs().max()),
        },
        "return_stream": {
            "return_column": return_stream.column,
            "return_stream_status": return_stream.status,
            "return_stream_reason": return_stream.reason,
            "return_stream_source": return_stream.source,
            "pnl_enabled": return_stream.pnl_enabled,
        },
        "features": {
            "candidate_count": len(feature_cols),
            "excluded_counts": exclusions,
            "exclusion_policy": (
                "exclude selected label, all label/target/Z4/forward-looking "
                "columns, time/date columns, and nonnumeric columns"
            ),
            "selector_policy": (
                "train-fold coverage >= 5 percent, median imputer, RobustScaler, "
                "VarianceThreshold; all fit on train only"
            ),
            "mean_feature_count_used": finite_mean(feature_counts),
        },
        "folds": {
            "requested_folds": args.folds,
            "valid_folds": len(valid_rows),
            "rows": [
                {
                    "fold": fold.number,
                    "train": [fold.train_start, fold.train_end],
                    "embargo": [fold.embargo_start, fold.embargo_end],
                    "test": [fold.test_start, fold.test_end],
                }
                for fold in folds
            ],
        },
        "aggregates": {
            "mean_auc": finite_mean(aucs),
            "mean_balanced_accuracy": finite_mean(balanced),
            "mean_model_return_after_cost": finite_mean(returns),
            "mean_excess_over_best_baseline": finite_mean(excesses),
            "mean_feature_count_used": finite_mean(feature_counts),
        },
        "stability": stability,
    }

    verdict, reason = verdict_from_summary(summary)
    summary["verdict"] = verdict
    summary["verdict_reason"] = reason

    return rows, summary


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)

    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows([{key: json_safe(row.get(key)) for key in fieldnames} for row in rows])


def write_summary_md(path: Path, summary: dict[str, Any]) -> None:
    aggregates = summary["aggregates"]
    stability = summary["stability"]
    config = summary["config"]
    dataset = summary["dataset"]
    features = summary["features"]
    return_stream = summary["return_stream"]
    warnings = summary.get("warnings", [])

    lines = [
        "# HYDRA Signal Validation Summary",
        "",
        f"- Run ID: `{summary['run_id']}`",
        f"- Verdict: `{summary['verdict']}`",
        f"- Reason: {summary['verdict_reason']}",
        f"- Dataset: `{config['dataset']}`",
        f"- Label column: `{config['label_column']}`",
        f"- Label mode: `{dataset['label_mode']}`",
        f"- Return column: `{return_stream['return_column']}`",
        f"- Return stream status: `{return_stream['return_stream_status']}`",
        f"- PnL enabled: `{return_stream['pnl_enabled']}`",
        f"- Rows after label drop: {dataset['rows_after_label_drop']}",
        f"- Candidate features: {features['candidate_count']}",
        f"- Mean used features: {aggregates['mean_feature_count_used']}",
        f"- Folds: {summary['folds']['valid_folds']}/{summary['folds']['requested_folds']}",
        f"- Embargo bars: {config['embargo_bars']}",
        f"- Cost bps: {config['cost_bps']}",
        "",
        "## Aggregate Metrics",
        "",
        f"- Mean AUC: {aggregates['mean_auc']}",
        f"- Mean balanced accuracy: {aggregates['mean_balanced_accuracy']}",
        f"- Mean model return after cost: {aggregates['mean_model_return_after_cost']}",
        f"- Mean excess over best baseline: {aggregates['mean_excess_over_best_baseline']}",
        "",
    ]

    if warnings:
        lines.extend(["## Warnings", ""])
        lines.extend(f"- {warning}" for warning in warnings)
        lines.append("")

    if not return_stream["pnl_enabled"]:
        lines.extend(
            [
                "## Return Stream Warning",
                "",
                "classification-only: no valid forward return stream",
                "",
                (
                    "PnL and baseline return metrics are disabled because no valid "
                    "separate return stream was available."
                ),
                "",
                f"Reason: {return_stream['return_stream_reason']}",
                "",
            ]
        )

    lines.extend(
        [
            "## Stability",
            "",
            f"- AUC above 0.50 fold rate: {stability['auc_above_50_fold_rate']}",
            f"- Positive return fold rate: {stability['positive_return_fold_rate']}",
            f"- Baseline beaten fold rate: {stability['baseline_beaten_fold_rate']}",
            f"- Return after cost std: {stability['return_after_cost_std']}",
            f"- Excess over baseline std: {stability['excess_over_baseline_std']}",
            "",
            "## Leakage Controls",
            "",
            "- Chronological expanding walk-forward folds only.",
            "- Embargo gap enforced between train and test windows.",
            "- Imputer, scaler, variance selector, and model are fit on train folds only.",
            "- Fixed 0.5 decision threshold; no test-threshold tuning.",
            "- Labels, forward-return columns, time/date columns, and nonnumeric columns are excluded from features.",
            "- PnL uses only `--return-column` or a safely auto-detected forward-return column, never a binary label by default.",
        ]
    )
    path.write_text("\n".join(lines) + "\n")


def write_outputs(
    output_dir: Path,
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
) -> None:
    run_dir = output_dir / summary["run_id"]
    run_dir.mkdir(parents=True, exist_ok=False)

    fold_results_path = run_dir / "fold_results.csv"
    summary_json_path = run_dir / "summary.json"
    summary_md_path = run_dir / "summary.md"

    write_csv(fold_results_path, rows)
    summary_json_path.write_text(json.dumps(json_safe(summary), indent=2) + "\n")
    write_summary_md(summary_md_path, summary)

    print(f"RUN_ID: {summary['run_id']}")
    print(f"VERDICT: {summary['verdict']}")
    print(f"FOLD_RESULTS: {fold_results_path}")
    print(f"SUMMARY_JSON: {summary_json_path}")
    print(f"SUMMARY_MD: {summary_md_path}")


def main() -> int:
    args = parse_args()
    rows, summary = run_validation(args)
    write_outputs(Path(args.output_dir), rows, summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
