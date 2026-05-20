"""Autonomous improvement loop — runs until all targets hit."""
from __future__ import annotations

import time
import json
from pathlib import Path
from typing import Optional

import numpy as np

from hydra.config import (
    ARTIFACTS, CV, TARGET, BACKTEST, STOP, ENSEMBLE,
    DB_PATH,
)
from hydra.data.loader import get_connection, merge_all
from hydra.data.targets import wilder_atr, make_targets
from hydra.data.cv import walk_forward_splits
from hydra.data.normalize import RobustScaler
from hydra.data.features import select_features, assemble_features
from hydra.backtest.engine_py import run_backtest, backtest_metrics
from hydra.signals.ensemble import bma_weights, bma_predict, threshold_signal
from hydra.signals.core import fuse_brains, agreement_multiplier, conflict_resolution
from hydra.brains.scalp import ScalpBrain
from hydra.brains.day import DayBrain
from hydra.brains.swing import SwingBrain
from hydra.loop.stopping import hit_targets, edge_decayed, drawdown_kill
from hydra.loop.strategies import STRATEGY_LADDER, get_strategy
from hydra.storage.duckdb_writer import HydraDB
from hydra.ragd.memory import remember


class HydraImprover:
    """Main autonomous loop controller."""

    def __init__(self, brain: str = "all", no_loop: bool = False):
        self.brain = brain
        self.no_loop = no_loop
        self.db = HydraDB()
        self.iteration = self.db.get_last_iteration()
        self.stagnation_count = 0
        self.best_sharpe = -np.inf
        self.strategy_index = 0
        self.kelly_frac = BACKTEST.kelly_frac

    def run(self) -> dict:
        """Execute the full training + improvement loop."""
        con = get_connection()
        df = merge_all(con, tf="h1")
        con.close()

        high = df["high"].values.astype(np.float64)
        low = df["low"].values.astype(np.float64)
        close = df["close"].values.astype(np.float64)
        atr = wilder_atr(high, low, close)
        y = make_targets(high, low, close)

        n_total = len(df)
        print(f"Data loaded: {n_total} bars, {df.shape[1]} columns")

        splits = walk_forward_splits(n_total)
        if not splits:
            return {"error": "insufficient data for walk-forward"}

        last_split = splits[-1]
        train_idx, val_idx, test_idx = last_split
        print(f"Split: train={len(train_idx)}, val={len(val_idx)}, test={len(test_idx)}")

        X_full, feat_names = assemble_features(
            df, train_idx, fold=0, col_names=list(df.columns))

        nan_cols = np.isnan(X_full).all(axis=0)
        X_full[:, nan_cols] = 0.0
        X_full = np.nan_to_num(X_full, nan=0.0, posinf=0.0, neginf=0.0)
        print(f"Features assembled: {X_full.shape[1]} raw features")

        y_train = y[train_idx]
        valid_tr_mask = np.isfinite(y_train)
        if valid_tr_mask.sum() < 50:
            return {"error": f"only {valid_tr_mask.sum()} valid training labels"}

        selected_idx, selected_names = select_features(
            X_full[train_idx][valid_tr_mask], y_train[valid_tr_mask],
            feat_names, fold=0)
        X_sel = X_full[:, selected_idx].copy()
        print(f"Selected {len(selected_idx)} features after MI+IC filter")

        scaler = RobustScaler()
        X_sel[train_idx] = scaler.fit_transform(X_sel[train_idx])
        X_sel[val_idx] = scaler.transform(X_sel[val_idx])
        X_sel[test_idx] = scaler.transform(X_sel[test_idx])
        scaler.save(0)

        X_tr, y_tr = X_sel[train_idx], y[train_idx]
        X_te, y_te = X_sel[test_idx], y[test_idx]

        valid_tr = np.isfinite(y_tr)
        valid_te = np.isfinite(y_te)
        X_tr_clean, y_tr_clean = X_tr[valid_tr], y_tr[valid_tr]
        X_te_clean = X_te[valid_te]
        print(f"Training samples: {len(y_tr_clean)}, Test samples: {valid_te.sum()}")

        scalp = ScalpBrain()
        day = DayBrain()
        swing = SwingBrain()

        print("Training scalp brain...")
        scalp.fit(X_tr_clean, y_tr_clean)
        print("Training day brain...")
        day.fit(X_tr_clean, y_tr_clean)
        print("Training swing brain...")
        swing.fit(X_tr_clean, y_tr_clean)

        while True:
            self.iteration += 1
            print(f"\n--- Iteration {self.iteration} ---")

            s_scalp = scalp.predict_proba(X_te_clean) * 2 - 1
            s_day = day.predict_proba(X_te_clean) * 2 - 1
            s_swing = swing.predict_proba(X_te_clean) * 2 - 1

            fused = conflict_resolution(s_scalp, s_day, s_swing)
            agree_mult = agreement_multiplier(s_scalp, s_day, s_swing)

            signals = np.sign(fused).astype(np.int8)
            confidences = np.abs(fused)
            confidences = np.clip(confidences, 0, 1)

            atr_te = atr[test_idx][valid_te]
            high_te = high[test_idx][valid_te]
            low_te = low[test_idx][valid_te]
            close_te = close[test_idx][valid_te]

            trades, equity = run_backtest(
                close_te, high_te, low_te, atr_te,
                signals, confidences, agree_mult,
                capital=BACKTEST.capital,
            )

            metrics = backtest_metrics(trades, equity)
            metrics["profit"] = equity[-1] - BACKTEST.capital if len(equity) > 0 else 0

            print(f"  Sharpe={metrics['sharpe']:.2f} WR={metrics['win_rate']:.1%} "
                  f"RR={metrics['rr']:.2f} Profit=${metrics['profit']:.0f} "
                  f"Trades={metrics['n_trades']}")

            iter_record = {
                "iter": self.iteration,
                "sharpe": metrics["sharpe"],
                "win_rate": metrics["win_rate"],
                "rr": metrics["rr"],
                "profit": metrics["profit"],
                "dd": metrics["max_dd"],
                "n_trades": metrics["n_trades"],
                "config": {"strategy_index": self.strategy_index},
            }
            self.db.write_iteration(iter_record)
            remember("hydra_iteration", iter_record)

            if hit_targets(metrics):
                print("\n*** ALL TARGETS HIT ***")
                self._finalize(metrics)
                return metrics

            if self.no_loop:
                print("--no-loop: exiting after one iteration")
                return metrics

            if metrics["sharpe"] > self.best_sharpe:
                self.best_sharpe = metrics["sharpe"]
                self.stagnation_count = 0
            else:
                self.stagnation_count += 1

            if self.stagnation_count >= 5:
                self.strategy_index += 1
                self.stagnation_count = 0

            if drawdown_kill(metrics["max_dd"]):
                self.kelly_frac *= 0.5
                remember("hydra_risk", {"event": "RISK_KILL_SWITCH",
                                        "iter": self.iteration})

            strategy = get_strategy(self.strategy_index)
            print(f"  Applying strategy: {strategy.name}")
            strategy.apply({"sharpe": metrics["sharpe"],
                           "win_rate": metrics["win_rate"]})

            if self.iteration >= 100:
                print("Max iterations (100) reached")
                return metrics

    def _finalize(self, metrics: dict):
        """Write final report to DB and RAGD."""
        report = {
            "sharpe": metrics["sharpe"],
            "win_rate": metrics["win_rate"],
            "rr": metrics["rr"],
            "profit": metrics["profit"],
            "config": {},
            "feature_importance": [],
        }
        self.db.write_final(report)
        remember("hydra_complete", report)

        print(f"""
==================== HYDRA FINAL REPORT ====================
Sharpe        : {metrics['sharpe']:.2f}
Sortino       : {metrics.get('sortino', 0):.2f}
Calmar        : {metrics.get('calmar', 0):.2f}
Win Rate      : {metrics['win_rate']:.1%}
Avg RR        : {metrics['rr']:.2f}
Profit Factor : {metrics.get('profit_factor', 0):.2f}
Max Drawdown  : {metrics.get('max_dd', 0):.1%}
Total Profit  : ${metrics['profit']:.0f}
Trades        : {metrics['n_trades']}
Iterations    : {self.iteration}
============================================================
""")
