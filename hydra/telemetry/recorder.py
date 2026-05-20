"""Telemetry recorder — writes iteration packets, CSVs, curves."""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from hydra.telemetry.schema import empty_packet
from hydra.utils.atomic import atomic_write_json
from hydra.utils.system_monitor import get_system_stats


class TelemetryRecorder:
    def __init__(self, run_dir: Path, run_id: str, max_iterations: int = 100):
        self.run_dir = run_dir
        self.run_id = run_id
        self.max_iterations = max_iterations
        self.tel_dir = run_dir / "telemetry"
        self.packets_dir = self.tel_dir / "packets"
        self.curves_dir = self.tel_dir / "curves"
        self.trades_dir = self.tel_dir / "trades"
        self.features_dir = self.tel_dir / "features"
        self.predictions_dir = self.tel_dir / "predictions"
        self.thresholds_dir = self.tel_dir / "thresholds"
        self.calibration_dir = self.tel_dir / "calibration"
        self.confusion_dir = self.tel_dir / "confusion"
        self.neural_dir = self.tel_dir / "neural"
        self.system_dir = self.tel_dir / "system"
        self.errors_dir = self.tel_dir / "errors"

        for d in [self.tel_dir, self.packets_dir, self.curves_dir, self.trades_dir,
                  self.features_dir, self.predictions_dir, self.thresholds_dir,
                  self.calibration_dir, self.confusion_dir, self.neural_dir,
                  self.system_dir, self.errors_dir]:
            d.mkdir(parents=True, exist_ok=True)

        self._prev_packet: Optional[dict] = None
        self._start_time = time.time()
        self._packets_written = 0

    def record_iteration(self, iteration: int, mode: str, seed: int,
                         models: list, X_train, y_train, X_val, y_val,
                         proba_val, sig_val, conf_val,
                         trades_val: list, equity_val,
                         metrics_val: dict, feat_cols: list,
                         train_trades: list = None, train_equity=None,
                         train_metrics: dict = None,
                         data_info: dict = None, targets_info: dict = None,
                         iter_start: float = None) -> dict:
        """Record full telemetry for one iteration."""
        now = time.time()
        packet = empty_packet(self.run_id, iteration, self.max_iterations, mode)
        packet["timestamp"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

        # Timing
        iter_seconds = now - iter_start if iter_start else None
        elapsed = now - self._start_time
        iph = (iteration / elapsed * 3600) if elapsed > 0 and iteration > 0 else None
        packet["timing"] = {
            "iteration_started_at": datetime.fromtimestamp(iter_start, tz=timezone.utc).isoformat() if iter_start else None,
            "iteration_finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "iteration_seconds": round(iter_seconds, 2) if iter_seconds else None,
            "elapsed_seconds": round(elapsed, 1),
            "eta_seconds": round((self.max_iterations - iteration) * (elapsed / iteration), 0) if iteration > 0 else None,
            "eta_human": self._format_eta((self.max_iterations - iteration) * (elapsed / iteration)) if iteration > 0 else "warming up",
            "iterations_per_hour": round(iph, 1) if iph else None,
            "packets_written": self._packets_written + 1,
            "events_written": None,
            "last_packet_age_seconds": 0,
        }

        # Data
        if data_info:
            packet["data"].update({k: v for k, v in data_info.items() if k in packet["data"]})

        # Features
        packet["features"]["feature_count"] = len(feat_cols)
        if X_train is not None:
            X_t = np.asarray(X_train)
            stds = np.std(X_t, axis=0)
            means_abs = np.mean(np.abs(X_t), axis=0)
            packet["features"]["feature_mean_abs_mean"] = round(float(np.mean(means_abs)), 4)
            packet["features"]["feature_std_mean"] = round(float(np.mean(stds)), 4)
            packet["features"]["feature_std_min"] = round(float(np.min(stds)), 6)
            packet["features"]["feature_std_max"] = round(float(np.max(stds)), 4)
            packet["features"]["feature_abs_max"] = round(float(np.max(np.abs(X_t))), 4)
            packet["features"]["constant_feature_count"] = int(np.sum(stds < 1e-10))
            nan_per_feat = np.sum(~np.isfinite(X_t), axis=0)
            packet["features"]["nan_feature_count"] = int(np.sum(nan_per_feat > 0))

            # Top importance from tree models
            importances = self._get_feature_importances(models, feat_cols)
            if importances:
                packet["features"]["top_importance_features"] = importances[:10]
                # Write CSV
                imp_df = pd.DataFrame(importances)
                imp_df["iteration"] = iteration
                imp_df["mode"] = mode
                imp_df.to_csv(str(self.features_dir / f"iter_{iteration:03d}_{mode}_feature_importance.csv"), index=False)

        # Targets
        if targets_info:
            packet["targets"].update(targets_info)

        # Model
        packet["model"]["seed"] = seed
        packet["model"]["mode"] = mode
        if models:
            model_names = [name for name, _ in models]
            packet["model"]["model_family"] = "ensemble"
            packet["model"]["model_name"] = "+".join(model_names)
            # Extract hyperparams from first tree model
            for mname, m in models:
                if hasattr(m, "n_estimators"):
                    packet["model"]["n_estimators"] = getattr(m, "n_estimators", None)
                    packet["model"]["max_depth"] = getattr(m, "max_depth", None)
                    packet["model"]["learning_rate"] = getattr(m, "learning_rate_", None) or getattr(m, "learning_rate", None)
                    break

        # Training metrics
        if train_metrics:
            for k, v in train_metrics.items():
                pk = f"train_{k}" if not k.startswith("train_") else k
                if pk in packet["training"]:
                    packet["training"][pk] = v
        if train_trades is not None:
            packet["training"]["train_trades"] = len(train_trades)
            if train_trades:
                pnls = [t.pnl_dollars for t in train_trades]
                packet["training"]["train_long_trades"] = sum(1 for t in train_trades if t.direction == 1)
                packet["training"]["train_short_trades"] = sum(1 for t in train_trades if t.direction == -1)
                packet["training"]["train_best_trade"] = round(max(pnls), 2)
                packet["training"]["train_worst_trade"] = round(min(pnls), 2)
                packet["training"]["train_avg_holding_bars"] = round(np.mean([t.bars_held for t in train_trades]), 1)
        if train_equity is not None and len(train_equity) > 0:
            packet["training"]["train_equity_start"] = round(float(train_equity[0]), 2)
            packet["training"]["train_equity_end"] = round(float(train_equity[-1]), 2)
            packet["training"]["train_equity_min"] = round(float(np.min(train_equity)), 2)
            packet["training"]["train_equity_max"] = round(float(np.max(train_equity)), 2)

        # Validation metrics
        if metrics_val:
            mapping = {"n_trades": "validation_trades", "sharpe": "validation_sharpe",
                       "sortino": "validation_sortino", "calmar": "validation_calmar",
                       "profit_factor": "validation_profit_factor", "win_rate": "validation_win_rate",
                       "avg_rr": "validation_avg_rr", "total_profit": "validation_total_profit",
                       "max_dd": "validation_max_drawdown", "expectancy": "validation_expectancy"}
            for k, pk in mapping.items():
                if k in metrics_val and pk in packet["validation"]:
                    packet["validation"][pk] = metrics_val[k]
        if trades_val is not None:
            packet["validation"]["validation_trades"] = len(trades_val)
            if trades_val:
                pnls = [t.pnl_dollars for t in trades_val]
                packet["validation"]["validation_long_trades"] = sum(1 for t in trades_val if t.direction == 1)
                packet["validation"]["validation_short_trades"] = sum(1 for t in trades_val if t.direction == -1)
                packet["validation"]["validation_best_trade"] = round(max(pnls), 2)
                packet["validation"]["validation_worst_trade"] = round(min(pnls), 2)
                packet["validation"]["validation_avg_holding_bars"] = round(np.mean([t.bars_held for t in trades_val]), 1)
        if equity_val is not None and len(equity_val) > 0:
            packet["validation"]["validation_equity_start"] = round(float(equity_val[0]), 2)
            packet["validation"]["validation_equity_end"] = round(float(equity_val[-1]), 2)
            packet["validation"]["validation_equity_min"] = round(float(np.min(equity_val)), 2)
            packet["validation"]["validation_equity_max"] = round(float(np.max(equity_val)), 2)
            # Write equity curve
            eq_df = pd.DataFrame({"equity": equity_val})
            eq_df.to_csv(str(self.curves_dir / f"iter_{iteration:03d}_{mode}_validation_equity.csv"), index=False)

        # Predictions
        if proba_val is not None:
            pv = np.asarray(proba_val)
            packet["predictions"]["validation_prediction_count"] = len(pv)
            packet["predictions"]["validation_prob_mean"] = round(float(np.mean(pv)), 4)
            packet["predictions"]["validation_prob_std"] = round(float(np.std(pv)), 4)
            packet["predictions"]["validation_prob_min"] = round(float(np.min(pv)), 4)
            packet["predictions"]["validation_prob_max"] = round(float(np.max(pv)), 4)
            for pctl, key in [(1, "p01"), (5, "p05"), (25, "p25"), (50, "p50"),
                              (75, "p75"), (95, "p95"), (99, "p99")]:
                packet["predictions"][f"validation_prob_{key}"] = round(float(np.percentile(pv, pctl)), 4)
            if sig_val is not None:
                sv = np.asarray(sig_val)
                packet["predictions"]["validation_signal_long_count"] = int(np.sum(sv == 1))
                packet["predictions"]["validation_signal_short_count"] = int(np.sum(sv == -1))
                packet["predictions"]["validation_signal_flat_count"] = int(np.sum(sv == 0))

        # Calibration & confusion
        if y_val is not None and proba_val is not None:
            yv = np.asarray(y_val)
            valid = np.isfinite(yv)
            if valid.sum() > 10:
                yv_clean = yv[valid]
                pv_clean = np.asarray(proba_val)[valid]
                try:
                    from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score, average_precision_score
                    packet["calibration"]["brier_score"] = round(float(brier_score_loss(yv_clean, pv_clean)), 4)
                    packet["calibration"]["log_loss"] = round(float(log_loss(yv_clean, np.clip(pv_clean, 1e-7, 1-1e-7))), 4)
                    if len(np.unique(yv_clean)) == 2:
                        packet["calibration"]["auc"] = round(float(roc_auc_score(yv_clean, pv_clean)), 4)
                        packet["calibration"]["average_precision"] = round(float(average_precision_score(yv_clean, pv_clean)), 4)
                except Exception:
                    pass
                # Confusion at 0.5 threshold
                pred_binary = (pv_clean > 0.5).astype(int)
                tp = int(np.sum((pred_binary == 1) & (yv_clean == 1)))
                tn = int(np.sum((pred_binary == 0) & (yv_clean == 0)))
                fp = int(np.sum((pred_binary == 1) & (yv_clean == 0)))
                fn = int(np.sum((pred_binary == 0) & (yv_clean == 1)))
                total = tp + tn + fp + fn
                packet["confusion"] = {
                    "tp": tp, "tn": tn, "fp": fp, "fn": fn,
                    "accuracy": round((tp + tn) / total, 4) if total > 0 else None,
                    "precision": round(tp / (tp + fp), 4) if (tp + fp) > 0 else None,
                    "recall": round(tp / (tp + fn), 4) if (tp + fn) > 0 else None,
                    "f1": round(2 * tp / (2 * tp + fp + fn), 4) if (2 * tp + fp + fn) > 0 else None,
                    "balanced_accuracy": None, "mcc": None,
                }

        # Trades telemetry
        if trades_val:
            pnls = np.array([t.pnl_dollars for t in trades_val])
            holds = [t.bars_held for t in trades_val]
            packet["trades"]["validation_trade_count"] = len(trades_val)
            packet["trades"]["long_count"] = sum(1 for t in trades_val if t.direction == 1)
            packet["trades"]["short_count"] = sum(1 for t in trades_val if t.direction == -1)
            packet["trades"]["best_trade"] = round(float(np.max(pnls)), 2) if len(pnls) > 0 else None
            packet["trades"]["worst_trade"] = round(float(np.min(pnls)), 2) if len(pnls) > 0 else None
            packet["trades"]["mean_trade"] = round(float(np.mean(pnls)), 2) if len(pnls) > 0 else None
            packet["trades"]["median_trade"] = round(float(np.median(pnls)), 2) if len(pnls) > 0 else None
            packet["trades"]["std_trade"] = round(float(np.std(pnls)), 2) if len(pnls) > 0 else None
            packet["trades"]["avg_holding_bars"] = round(float(np.mean(holds)), 1) if holds else None
            packet["trades"]["median_holding_bars"] = round(float(np.median(holds)), 1) if holds else None
            # Win/loss streaks
            outcomes = [1 if t.pnl_dollars > 0 else -1 for t in trades_val]
            ws, ls, cw, cl = 0, 0, 0, 0
            for o in outcomes:
                if o == 1: cw += 1; cl = 0
                else: cl += 1; cw = 0
                ws = max(ws, cw); ls = max(ls, cl)
            packet["trades"]["win_streak_max"] = ws
            packet["trades"]["loss_streak_max"] = ls

        # Risk
        if equity_val is not None and len(equity_val) > 1:
            rets = np.diff(equity_val) / np.where(equity_val[:-1] > 0, equity_val[:-1], 1.0)
            rets = rets[np.isfinite(rets)]
            if len(rets) > 5:
                packet["risk"]["skew"] = round(float(pd.Series(rets).skew()), 4)
                packet["risk"]["kurtosis"] = round(float(pd.Series(rets).kurtosis()), 4)
                packet["risk"]["var_95"] = round(float(np.percentile(rets, 5)), 6)
                packet["risk"]["cvar_95"] = round(float(np.mean(rets[rets <= np.percentile(rets, 5)])), 6)
                packet["risk"]["worst_day"] = round(float(np.min(rets)), 6)
                packet["risk"]["best_day"] = round(float(np.max(rets)), 6)
                if np.percentile(rets, 5) != 0:
                    packet["risk"]["tail_ratio"] = round(float(np.percentile(rets, 95) / abs(np.percentile(rets, 5))), 4)

        # System
        packet["system"] = get_system_stats()
        packet["system"]["python_pid"] = os.getpid()
        packet["system"]["runner_process_alive"] = True

        # Deltas
        if self._prev_packet:
            prev_val = self._prev_packet.get("validation", {})
            cur_val = packet["validation"]
            packet["deltas"]["validation_sharpe_delta"] = self._delta(cur_val.get("validation_sharpe"), prev_val.get("validation_sharpe"))
            packet["deltas"]["validation_profit_factor_delta"] = self._delta(cur_val.get("validation_profit_factor"), prev_val.get("validation_profit_factor"))
            packet["deltas"]["validation_trades_delta"] = self._delta(cur_val.get("validation_trades"), prev_val.get("validation_trades"))
            packet["deltas"]["validation_profit_delta"] = self._delta(cur_val.get("validation_total_profit"), prev_val.get("validation_total_profit"))
            prev_timing = self._prev_packet.get("timing", {})
            packet["deltas"]["iteration_seconds_delta"] = self._delta(
                packet["timing"].get("iteration_seconds"), prev_timing.get("iteration_seconds"))

        # Write packet
        packet_path = self.packets_dir / f"iteration_{iteration:03d}.json"
        atomic_write_json(packet_path, packet)

        # Append to iterations.jsonl
        jsonl_path = self.tel_dir / "iterations.jsonl"
        with open(jsonl_path, "a") as f:
            f.write(json.dumps(packet, default=str) + "\n")
            f.flush()

        # Append summary to CSV
        self._append_iteration_csv(iteration, mode, seed, metrics_val, packet)

        self._prev_packet = packet
        self._packets_written += 1
        return packet

    def _get_feature_importances(self, models: list, feat_cols: list) -> list:
        importances = []
        for name, model in models:
            imp = None
            if hasattr(model, "feature_importances_"):
                imp = model.feature_importances_
            elif hasattr(model, "coef_"):
                imp = np.abs(model.coef_).flatten()
            if imp is not None and len(imp) == len(feat_cols):
                top_idx = np.argsort(imp)[::-1][:15]
                for rank, idx in enumerate(top_idx):
                    importances.append({
                        "feature": feat_cols[idx],
                        "importance": round(float(imp[idx]), 6),
                        "rank": rank + 1,
                        "model": name,
                    })
                break  # Use first model with importances
        return importances

    def _delta(self, cur, prev) -> Optional[float]:
        if cur is None or prev is None:
            return None
        try:
            return round(float(cur) - float(prev), 4)
        except (TypeError, ValueError):
            return None

    def _format_eta(self, seconds: float) -> str:
        if seconds is None or seconds < 0:
            return "N/A"
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def _append_iteration_csv(self, iteration: int, mode: str, seed: int,
                              metrics: dict, packet: dict) -> None:
        csv_path = self.tel_dir / "iteration_metrics.csv"
        row = {
            "iteration": iteration, "mode": mode, "seed": seed,
            "sharpe": metrics.get("sharpe"), "sortino": metrics.get("sortino"),
            "profit_factor": metrics.get("profit_factor"),
            "win_rate": metrics.get("win_rate"), "n_trades": metrics.get("n_trades"),
            "total_profit": metrics.get("total_profit"), "max_dd": metrics.get("max_dd"),
            "prob_mean": packet["predictions"].get("validation_prob_mean"),
            "prob_std": packet["predictions"].get("validation_prob_std"),
            "auc": packet["calibration"].get("auc"),
            "iter_seconds": packet["timing"].get("iteration_seconds"),
        }
        df = pd.DataFrame([row])
        df.to_csv(str(csv_path), mode="a", header=not csv_path.exists(), index=False)

    def record_system_snapshot(self) -> None:
        stats = get_system_stats()
        stats["timestamp"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        stats["python_pid"] = os.getpid()
        csv_path = self.tel_dir / "system_metrics.csv"
        df = pd.DataFrame([stats])
        df.to_csv(str(csv_path), mode="a", header=not csv_path.exists(), index=False)
