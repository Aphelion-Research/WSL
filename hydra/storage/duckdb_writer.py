"""DuckDB persistence for HYDRA iterations, trades, and models."""
from __future__ import annotations

import json
from typing import Optional

import duckdb
import numpy as np

from hydra.config import DB_PATH

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS hydra_iterations (
    iter        INTEGER PRIMARY KEY,
    config_json JSON,
    sharpe      DOUBLE, win_rate DOUBLE, rr DOUBLE, profit DOUBLE,
    dd          DOUBLE, n_trades INTEGER, ts TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS hydra_trades (
    iter        INTEGER, entry_ts TIMESTAMP, exit_ts TIMESTAMP,
    direction   TINYINT, entry_px DOUBLE, exit_px DOUBLE,
    pnl         DOUBLE, bars_held INTEGER, brain VARCHAR
);

CREATE TABLE IF NOT EXISTS hydra_models (
    iter        INTEGER, model_name VARCHAR,
    val_sharpe  DOUBLE, feature_importance_json JSON
);

CREATE TABLE IF NOT EXISTS hydra_signals (
    ts TIMESTAMP, signal TINYINT, confidence DOUBLE,
    regime VARCHAR, brain_source VARCHAR
);

CREATE TABLE IF NOT EXISTS hydra_final (
    sharpe DOUBLE, win_rate DOUBLE, rr DOUBLE, profit DOUBLE,
    config_json JSON, feature_importance_json JSON,
    finalized_ts TIMESTAMP DEFAULT now()
);
"""


class HydraDB:
    """Writer for all hydra_* tables."""

    def __init__(self, db_path: str | None = None):
        self.db_path = str(db_path or DB_PATH)
        self._ensure_schema()

    def _get_con(self) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(self.db_path)

    def _ensure_schema(self):
        con = self._get_con()
        for stmt in SCHEMA_SQL.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                con.execute(stmt)
        con.close()

    def write_iteration(self, iteration: dict):
        con = self._get_con()
        con.execute(
            "INSERT OR REPLACE INTO hydra_iterations "
            "(iter, config_json, sharpe, win_rate, rr, profit, dd, n_trades) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                iteration["iter"],
                json.dumps(iteration.get("config", {})),
                iteration.get("sharpe", 0),
                iteration.get("win_rate", 0),
                iteration.get("rr", 0),
                iteration.get("profit", 0),
                iteration.get("dd", 0),
                iteration.get("n_trades", 0),
            ],
        )
        con.close()

    def write_trades(self, iter_num: int, trades: list[dict], brain: str = "all"):
        con = self._get_con()
        for t in trades:
            con.execute(
                "INSERT INTO hydra_trades "
                "(iter, entry_ts, exit_ts, direction, entry_px, exit_px, pnl, bars_held, brain) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    iter_num,
                    t.get("entry_ts"),
                    t.get("exit_ts"),
                    t.get("direction", 0),
                    t.get("entry_px", 0),
                    t.get("exit_px", 0),
                    t.get("pnl", 0),
                    t.get("bars_held", 0),
                    brain,
                ],
            )
        con.close()

    def write_model(self, iter_num: int, model_name: str, val_sharpe: float,
                    importance: Optional[np.ndarray] = None):
        con = self._get_con()
        imp_json = json.dumps(importance.tolist()) if importance is not None else "[]"
        con.execute(
            "INSERT INTO hydra_models (iter, model_name, val_sharpe, feature_importance_json) "
            "VALUES (?, ?, ?, ?)",
            [iter_num, model_name, val_sharpe, imp_json],
        )
        con.close()

    def write_final(self, report: dict):
        con = self._get_con()
        con.execute(
            "INSERT INTO hydra_final (sharpe, win_rate, rr, profit, config_json, feature_importance_json) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [
                report.get("sharpe", 0),
                report.get("win_rate", 0),
                report.get("rr", 0),
                report.get("profit", 0),
                json.dumps(report.get("config", {})),
                json.dumps(report.get("feature_importance", [])),
            ],
        )
        con.close()

    def get_last_iteration(self) -> int:
        con = self._get_con()
        result = con.execute(
            "SELECT COALESCE(MAX(iter), 0) FROM hydra_iterations"
        ).fetchone()
        con.close()
        return result[0] if result else 0
