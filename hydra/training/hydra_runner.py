"""HYDRA training runner - integrate with 3,000-column matrix.

Adapts existing hydra/loop/improver.py to use:
- Agent 1's matrix (3,000 cols)
- Enhanced labels from triple_barrier.py
- Chronological splits with embargo/purge
- Training guardrails (gate check)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from hydra.config import ARTIFACTS, TARGET, BACKTEST, ROOT
from hydra.labels.triple_barrier import TripleBarrierLabeler, compute_label_statistics
from hydra.training.splits import ChronologicalSplit, validate_split_safety
from hydra.training.guardrails import (
    TrainingGuardrails,
    check_training_allowed,
    exclude_non_features,
)
from hydra.data.normalize import RobustScaler
from hydra.brains.scalp import ScalpBrain
from hydra.brains.day import DayBrain
from hydra.brains.swing import SwingBrain
from hydra.backtest.engine_py import run_backtest, backtest_metrics
from hydra.signals.core import conflict_resolution, agreement_multiplier
from hydra.storage.duckdb_writer import HydraDB
from hydra.ragd.memory import remember


class HydraRunner:
    """HYDRA training runner for 3,000-column matrix."""

    def __init__(
        self,
        matrix_path: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        check_gates: bool = True,
        mode: str = "all",  # all, scalp, day, swing
    ):
        """Initialize runner.

        Args:
            matrix_path: Path to Agent 1's matrix parquet
            output_dir: Where to save artifacts
            check_gates: If True, check training guardrails before running
            mode: Which brains to train (all, scalp, day, swing)
        """
        if matrix_path is None:
            self.matrix_path = ROOT / "data" / "dataset_v1.parquet"
        else:
            self.matrix_path = Path(matrix_path)

        if output_dir is None:
            self.output_dir = ARTIFACTS
        else:
            self.output_dir = Path(output_dir)

        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.check_gates = check_gates
        self.mode = mode
        self.db = HydraDB()

    def load_and_validate(self) -> tuple[pd.DataFrame, bool, str]:
        """Load matrix and check training gates.

        Returns:
            (df, training_allowed, reason)
        """
        if not self.matrix_path.exists():
            return pd.DataFrame(), False, f"Matrix not found: {self.matrix_path}"

        print(f"Loading matrix from {self.matrix_path}...")
        df = pd.read_parquet(self.matrix_path)
        print(f"Loaded: {len(df):,} rows × {len(df.columns):,} columns")

        # Check training gates
        if self.check_gates:
            training_allowed, verdict = check_training_allowed(df=df)

            if not training_allowed:
                # Write blocked report
                guardrails = TrainingGuardrails()
                guardrails.write_blocked_report(verdict)
                return df, False, verdict.reason

        return df, True, "Gates passed"

    def generate_labels(
        self,
        df: pd.DataFrame,
    ) -> tuple[np.ndarray, dict]:
        """Generate labels using enhanced triple-barrier.

        Returns:
            (labels, metadata_dict)
        """
        print("Generating labels with enhanced triple-barrier...")

        labeler = TripleBarrierLabeler(
            atr_window=TARGET.atr_window,
            horizon_bars=TARGET.horizon_bars,
            stop_mult=TARGET.stop_mult,
            target_mult=TARGET.target_mult,
            min_atr_pct=0.0020,  # Agent 1 recommendation
            min_hold_bars=3,
            spread_to_atr_min=0.33,
            use_session_spread=True,
        )

        labels, metadata = labeler.fit_transform(df)

        print(f"Labels generated:")
        print(f"  Total bars: {metadata.total_bars:,}")
        print(f"  Labeled: {metadata.labeled_bars:,} ({metadata.label_rate:.1%})")
        print(f"  Long rate: {metadata.long_rate:.1%}")
        print(f"  Short rate: {metadata.short_rate:.1%}")
        print(f"  Both-hit rate: {metadata.both_hit_rate:.1%}")
        print(f"  Mean ATR: ${metadata.mean_atr:.2f} ({metadata.mean_atr_pct:.2%})")
        print(f"  Spread/ATR: {metadata.spread_to_atr_ratio:.1%}")

        # Log to RAGD
        remember("hydra_label_generation", {
            "label_rate": metadata.label_rate,
            "long_rate": metadata.long_rate,
            "mean_atr": metadata.mean_atr,
            "session_dist": metadata.session_distribution,
        })

        return labels, metadata.__dict__

    def prepare_features(
        self,
        df: pd.DataFrame,
    ) -> tuple[np.ndarray, list[str]]:
        """Prepare feature matrix (exclude non-features).

        Returns:
            (X, feature_names)
        """
        print("Preparing features...")

        # Exclude non-feature columns (Agent 2 mission requirement)
        df_features = exclude_non_features(
            df,
            label_col_pattern="label",
            quality_col_pattern="quality",
            reserved_cols=["timestamp", "date", "datetime", "id", "open", "high", "low", "close", "volume"],
        )

        # Convert to numpy
        X = df_features.values.astype(np.float32)
        feature_names = df_features.columns.tolist()

        # NaN handling
        all_nan_cols = np.isnan(X).all(axis=0)
        X[:, all_nan_cols] = 0.0
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

        print(f"Features prepared: {X.shape[1]:,} columns after NaN handling")

        return X, feature_names

    def train(
        self,
        df: pd.DataFrame,
        labels: np.ndarray,
        X: np.ndarray,
        feature_names: list[str],
    ) -> dict:
        """Train HYDRA brains and evaluate.

        Returns:
            Metrics dict
        """
        print("Creating chronological splits...")

        splitter = ChronologicalSplit(
            n_splits=1,  # Single split for now (can expand later)
            expanding_window=True,
        )

        try:
            train_idx, oos_idx, split_meta = splitter.get_oos_split(df, oos_frac=0.15)
        except ValueError as e:
            print(f"Split error: {e}")
            return {"error": str(e)}

        print(f"Split created:")
        print(f"  Train: {split_meta.train_size:,} bars ({split_meta.train_date_range[0]} to {split_meta.train_date_range[1]})")
        print(f"  OOS: {split_meta.test_size:,} bars ({split_meta.test_date_range[0]} to {split_meta.test_date_range[1]})")
        print(f"  Embargo: {split_meta.embargo_bars} bars")
        print(f"  Purge: {split_meta.purge_bars} bars")

        # Validate split safety
        safety_checks = validate_split_safety(
            train_idx, np.array([]), oos_idx, TARGET.horizon_bars, split_meta.embargo_bars
        )
        print(f"Split safety: {sum(safety_checks.values())}/{len(safety_checks)} checks passed")
        if not all(safety_checks.values()):
            failed = [k for k, v in safety_checks.items() if not v]
            print(f"  FAILED: {failed}")
            return {"error": f"Split safety failed: {failed}"}

        # Extract train/test data
        X_train, y_train = X[train_idx], labels[train_idx]
        X_oos, y_oos = X[oos_idx], labels[oos_idx]

        # Filter valid labels
        train_valid = np.isfinite(y_train)
        oos_valid = np.isfinite(y_oos)

        X_train_clean = X_train[train_valid]
        y_train_clean = y_train[train_valid]
        X_oos_clean = X_oos[oos_valid]

        print(f"Training samples: {len(y_train_clean):,} (from {len(y_train):,} total)")
        print(f"OOS samples: {oos_valid.sum():,} (from {len(y_oos):,} total)")

        if len(y_train_clean) < 100:
            return {"error": f"Insufficient training labels: {len(y_train_clean)}"}

        # Scale features
        print("Scaling features...")
        scaler = RobustScaler()
        X_train_scaled = scaler.fit_transform(X_train_clean)
        X_oos_scaled = scaler.transform(X_oos_clean)
        scaler.save(0)

        # Train brains
        print("Training brains...")
        brains = {}

        if self.mode in ["all", "scalp"]:
            print("  Training scalp brain...")
            scalp = ScalpBrain()
            scalp.fit(X_train_scaled, y_train_clean)
            brains["scalp"] = scalp

        if self.mode in ["all", "day"]:
            print("  Training day brain...")
            day = DayBrain()
            day.fit(X_train_scaled, y_train_clean)
            brains["day"] = day

        if self.mode in ["all", "swing"]:
            print("  Training swing brain...")
            swing = SwingBrain()
            swing.fit(X_train_scaled, y_train_clean)
            brains["swing"] = swing

        # Generate predictions
        print("Generating OOS predictions...")
        signals_dict = {}
        for name, brain in brains.items():
            proba = brain.predict_proba(X_oos_scaled)
            signals_dict[name] = proba * 2 - 1  # Convert [0,1] to [-1,1]

        # Ensemble fusion
        if len(brains) > 1:
            signal_arrays = list(signals_dict.values())
            fused = conflict_resolution(*signal_arrays)
            agree_mult = agreement_multiplier(*signal_arrays)
        else:
            fused = list(signals_dict.values())[0]
            agree_mult = np.ones(len(fused))

        signals = np.sign(fused).astype(np.int8)
        confidences = np.clip(np.abs(fused), 0, 1)

        # Backtest
        print("Running backtest...")
        high = df["high"].values[oos_idx][oos_valid]
        low = df["low"].values[oos_idx][oos_valid]
        close = df["close"].values[oos_idx][oos_valid]

        # Recompute ATR for OOS period
        from hydra.data.targets import wilder_atr
        atr_full = wilder_atr(df["high"].values, df["low"].values, df["close"].values)
        atr_oos = atr_full[oos_idx][oos_valid]

        trades, equity = run_backtest(
            close, high, low, atr_oos,
            signals, confidences, agree_mult,
            capital=BACKTEST.capital,
        )

        metrics = backtest_metrics(trades, equity)
        metrics["profit"] = equity[-1] - BACKTEST.capital if len(equity) > 0 else 0

        print("\n" + "=" * 60)
        print("BACKTEST RESULTS")
        print("=" * 60)
        print(f"Sharpe:        {metrics['sharpe']:.2f}")
        print(f"Sortino:       {metrics['sortino']:.2f}")
        print(f"Calmar:        {metrics['calmar']:.2f}")
        print(f"Win Rate:      {metrics['win_rate']:.1%}")
        print(f"Avg RR:        {metrics['rr']:.2f}")
        print(f"Profit Factor: {metrics['profit_factor']:.2f}")
        print(f"Max Drawdown:  {metrics['max_dd']:.1%}")
        print(f"Profit:        ${metrics['profit']:.0f}")
        print(f"Trades:        {metrics['n_trades']}")
        print("=" * 60 + "\n")

        # Save artifacts
        self._save_artifacts(
            brains, metrics, split_meta, feature_names, trades, equity
        )

        # Log to RAGD
        remember("hydra_training_complete", {
            "sharpe": metrics["sharpe"],
            "win_rate": metrics["win_rate"],
            "n_trades": metrics["n_trades"],
            "mode": self.mode,
        })

        return metrics

    def _save_artifacts(
        self,
        brains: dict,
        metrics: dict,
        split_meta,
        feature_names: list[str],
        trades: list,
        equity: np.ndarray,
    ) -> None:
        """Save models, metrics, configs, equity curve."""
        from datetime import datetime
        import pickle

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save models
        for name, brain in brains.items():
            model_path = self.output_dir / f"{name}_brain_{timestamp}.pkl"
            with open(model_path, "wb") as f:
                pickle.dump(brain, f)
            print(f"Saved {name} brain to {model_path}")

        # Save metrics
        metrics_path = self.output_dir / f"metrics_{timestamp}.json"
        with open(metrics_path, "w") as f:
            json.dump(metrics, f, indent=2)
        print(f"Saved metrics to {metrics_path}")

        # Save config
        config = {
            "mode": self.mode,
            "atr_window": TARGET.atr_window,
            "horizon_bars": TARGET.horizon_bars,
            "stop_mult": TARGET.stop_mult,
            "target_mult": TARGET.target_mult,
            "split_metadata": {
                "train_size": split_meta.train_size,
                "test_size": split_meta.test_size,
                "embargo_bars": split_meta.embargo_bars,
                "purge_bars": split_meta.purge_bars,
            },
            "n_features": len(feature_names),
        }
        config_path = self.output_dir / f"config_{timestamp}.json"
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        print(f"Saved config to {config_path}")

        # Save equity curve
        equity_df = pd.DataFrame({
            "bar": np.arange(len(equity)),
            "equity": equity,
        })
        equity_path = self.output_dir / f"equity_curve_{timestamp}.csv"
        equity_df.to_csv(equity_path, index=False)
        print(f"Saved equity curve to {equity_path}")

        # Save trades
        if trades:
            trades_df = pd.DataFrame([
                {
                    "entry_ts": t.entry_ts,
                    "exit_ts": t.exit_ts,
                    "direction": t.direction,
                    "entry_px": t.entry_px,
                    "exit_px": t.exit_px,
                    "pnl": t.pnl,
                    "bars_held": t.bars_held,
                    "size": t.size,
                }
                for t in trades
            ])
            trades_path = self.output_dir / f"trades_{timestamp}.csv"
            trades_df.to_csv(trades_path, index=False)
            print(f"Saved trades to {trades_path}")

    def run(self) -> dict:
        """Main entry point: load → validate → label → train → evaluate.

        Returns:
            Metrics dict (or error dict if blocked)
        """
        # Load and validate
        df, training_allowed, reason = self.load_and_validate()

        if not training_allowed:
            print(f"\n{'=' * 60}")
            print("TRAINING BLOCKED")
            print(f"{'=' * 60}")
            print(f"Reason: {reason}")
            print(f"{'=' * 60}\n")
            return {"error": "training_blocked", "reason": reason}

        # Generate labels
        labels, label_meta = self.generate_labels(df)

        # Check label rate
        if label_meta["label_rate"] < 0.30:
            print(f"WARNING: Low label rate ({label_meta['label_rate']:.1%})")

        # Prepare features
        X, feature_names = self.prepare_features(df)

        # Train and evaluate
        metrics = self.train(df, labels, X, feature_names)

        return metrics
