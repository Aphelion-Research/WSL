"""Telemetry packet schema — 1000-signal structure."""
from __future__ import annotations

from datetime import datetime, timezone


def empty_packet(run_id: str = "", iteration: int = 0, max_iterations: int = 100,
                 mode: str = "", symbol: str = "XAUUSD") -> dict:
    return {
        "schema_version": 2,
        "run_id": run_id,
        "run_type": "AVAILABLE_DATA_EQUAL_THIRDS",
        "strict_9year": False,
        "iteration": iteration,
        "max_iterations": max_iterations,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "phase": "TRAINING",
        "symbol": symbol,
        "mode": mode,
        "status": "running",
        "data": _empty_data(),
        "features": _empty_features(),
        "targets": _empty_targets(),
        "model": _empty_model(),
        "neural": {"is_neural": False, "reason": "N/A — current iteration uses non-neural model"},
        "training": _empty_metrics("train"),
        "validation": _empty_metrics("validation"),
        "predictions": _empty_predictions(),
        "thresholds": {"sweep_available": False, "best_threshold": None, "best_threshold_score": None,
                       "threshold_rows": None, "threshold_file": None},
        "calibration": {"brier_score": None, "log_loss": None, "ece": None, "auc": None,
                        "average_precision": None, "calibration_bins": None, "calibration_file": None},
        "confusion": {"tn": None, "fp": None, "fn": None, "tp": None, "accuracy": None,
                      "precision": None, "recall": None, "f1": None, "balanced_accuracy": None, "mcc": None},
        "classification": {},
        "backtest": {"engine": "hydra_py", "cost_scenario": None, "spread_cost_total": None,
                     "slippage_cost_total": None, "commission_total": None, "turnover": None,
                     "exposure_pct": None, "bars_in_market": None, "bars_flat": None,
                     "entry_count": None, "exit_count": None},
        "trades": _empty_trades(),
        "equity": {"train_equity_points": None, "validation_equity_points": None,
                   "train_equity_start": None, "train_equity_end": None,
                   "validation_equity_start": None, "validation_equity_end": None,
                   "validation_equity_file": None},
        "drawdown": {"train_max_dd": None, "validation_max_dd": None,
                     "train_dd_duration_max": None, "validation_dd_duration_max": None},
        "risk": {"max_drawdown": None, "avg_drawdown": None, "drawdown_duration_max": None,
                 "drawdown_duration_avg": None, "var_95": None, "cvar_95": None,
                 "worst_trade": None, "worst_day": None, "best_day": None,
                 "tail_ratio": None, "skew": None, "kurtosis": None},
        "regime": {},
        "costs": {"low": None, "base": None, "stress": None},
        "best_so_far": {"best_iteration": None, "best_sharpe": None, "best_pf": None,
                        "best_trades": None, "best_seed": None},
        "deltas": {"validation_sharpe_delta": None, "validation_profit_factor_delta": None,
                   "validation_trades_delta": None, "validation_profit_delta": None,
                   "validation_max_drawdown_delta": None, "iteration_seconds_delta": None,
                   "cpu_pct_delta": None, "gpu_util_delta": None, "ram_used_delta": None},
        "system": {},
        "files": {},
        "timing": {"iteration_started_at": None, "iteration_finished_at": None,
                   "iteration_seconds": None, "elapsed_seconds": None,
                   "eta_seconds": None, "eta_human": None, "iterations_per_hour": None,
                   "packets_written": None, "events_written": None, "last_packet_age_seconds": None},
        "warnings": [],
        "errors": [],
    }


def _empty_data() -> dict:
    return {
        "source": None, "provider": None, "timeframe": None,
        "rows_total": None, "train_rows": None, "validation_rows": None, "test_rows": None,
        "train_start": None, "train_end": None, "validation_start": None, "validation_end": None,
        "test_start": None, "test_end": None, "columns_total": None, "ohlcv_columns_present": None,
        "nan_total": None, "nan_pct": None, "inf_total": None,
        "duplicate_timestamp_count": None, "duplicate_timestamp_pct": None,
        "missing_timestamp_count": None, "timestamp_monotonic": None,
        "close_min": None, "close_max": None, "close_mean": None, "close_std": None, "close_last": None,
        "return_mean": None, "return_std": None, "return_skew": None, "return_kurtosis": None,
        "volume_min": None, "volume_max": None, "volume_mean": None, "volume_std": None,
        "spread_mean": None, "spread_std": None, "spread_max": None,
    }


def _empty_features() -> dict:
    return {
        "feature_count": None, "selected_feature_count": None, "dropped_feature_count": None,
        "constant_feature_count": None, "nan_feature_count": None, "inf_feature_count": None,
        "feature_mean_abs_mean": None, "feature_std_mean": None, "feature_std_min": None,
        "feature_std_max": None, "feature_abs_max": None,
        "top_nan_features": [], "top_constant_features": [], "top_correlated_features": [],
        "top_importance_features": [], "top_permutation_features": [],
        "feature_drift_train_vs_val": [], "feature_file": None,
    }


def _empty_targets() -> dict:
    return {
        "target_name": None, "train_class_balance": {},
        "validation_class_balance": {}, "test_class_balance": {},
        "train_positive_pct": None, "validation_positive_pct": None, "test_positive_pct": None,
        "label_horizon": None, "label_nan_count": None, "label_valid_count": None,
        "target_leakage_check": None,
    }


def _empty_model() -> dict:
    return {
        "model_family": None, "model_name": None, "seed": None, "mode": None,
        "hyperparameters": {}, "fit_seconds": None, "predict_seconds": None,
        "validation_seconds": None, "n_estimators": None, "max_depth": None,
        "learning_rate": None, "num_leaves": None, "subsample": None, "colsample": None,
        "regularization_l1": None, "regularization_l2": None,
        "parameter_count": None, "trainable_parameter_count": None,
        "model_size_bytes": None, "model_file": None,
    }


def _empty_metrics(prefix: str) -> dict:
    return {
        f"{prefix}_trades": None, f"{prefix}_sharpe": None, f"{prefix}_sortino": None,
        f"{prefix}_calmar": None, f"{prefix}_profit_factor": None, f"{prefix}_win_rate": None,
        f"{prefix}_avg_rr": None, f"{prefix}_total_profit": None, f"{prefix}_max_drawdown": None,
        f"{prefix}_expectancy": None, f"{prefix}_exposure_pct": None,
        f"{prefix}_long_trades": None, f"{prefix}_short_trades": None,
        f"{prefix}_best_trade": None, f"{prefix}_worst_trade": None,
        f"{prefix}_avg_holding_bars": None, f"{prefix}_equity_start": None,
        f"{prefix}_equity_end": None, f"{prefix}_equity_min": None, f"{prefix}_equity_max": None,
    }


def _empty_predictions() -> dict:
    return {
        "train_prediction_count": None, "validation_prediction_count": None,
        "train_prob_mean": None, "train_prob_std": None, "train_prob_min": None,
        "train_prob_p01": None, "train_prob_p05": None, "train_prob_p25": None,
        "train_prob_p50": None, "train_prob_p75": None, "train_prob_p95": None,
        "train_prob_p99": None, "train_prob_max": None,
        "validation_prob_mean": None, "validation_prob_std": None, "validation_prob_min": None,
        "validation_prob_p01": None, "validation_prob_p05": None, "validation_prob_p25": None,
        "validation_prob_p50": None, "validation_prob_p75": None, "validation_prob_p95": None,
        "validation_prob_p99": None, "validation_prob_max": None,
        "validation_signal_long_count": None, "validation_signal_short_count": None,
        "validation_signal_flat_count": None, "prediction_file": None,
    }


def _empty_trades() -> dict:
    return {
        "train_trade_count": None, "validation_trade_count": None,
        "long_count": None, "short_count": None, "flat_count": None,
        "best_trade": None, "worst_trade": None, "mean_trade": None,
        "median_trade": None, "std_trade": None,
        "win_streak_max": None, "loss_streak_max": None,
        "avg_holding_bars": None, "median_holding_bars": None, "trade_file": None,
    }
