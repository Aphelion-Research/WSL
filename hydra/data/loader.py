"""DuckDB data loaders — adapted to actual Dominion schema."""
from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd

from hydra.config import DB_PATH


def get_connection() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DB_PATH), read_only=True)


def load_bars(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    df = con.execute(
        "SELECT timestamp, open, high, low, close, volume "
        "FROM gold_master ORDER BY timestamp"
    ).df()
    df.rename(columns={"timestamp": "ts"}, inplace=True)
    return df


def load_features(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Pivot long-format features table to wide."""
    df = con.execute(
        "SELECT timestamp, feature_name, feature_value FROM features"
    ).df()
    df.rename(columns={"timestamp": "ts"}, inplace=True)
    wide = df.pivot_table(index="ts", columns="feature_name",
                          values="feature_value", aggfunc="first")
    wide = wide.reset_index()
    wide.columns.name = None
    return wide.sort_values("ts").reset_index(drop=True)


def load_macro(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Pivot long-format macro data to wide with series as columns."""
    df = con.execute(
        "SELECT timestamp, series_id, value FROM macro_data"
    ).df()
    df.rename(columns={"timestamp": "ts"}, inplace=True)
    wide = df.pivot_table(index="ts", columns="series_id",
                          values="value", aggfunc="first")
    wide = wide.reset_index()
    wide.columns.name = None
    return wide.sort_values("ts").reset_index(drop=True)


def load_cot(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    df = con.execute(
        "SELECT report_date AS ts, commercial_long, commercial_short, "
        "       noncommercial_long, noncommercial_short, open_interest "
        "FROM cot_data ORDER BY report_date"
    ).df()
    df["ts"] = pd.to_datetime(df["ts"])
    return df


def load_regimes(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    df = con.execute(
        "SELECT timestamp, macro_regime, structural_regime, "
        "       tactical_regime, micro_regime, confidence "
        "FROM regime_labels ORDER BY timestamp"
    ).df()
    df.rename(columns={"timestamp": "ts"}, inplace=True)
    return df


def merge_all(con: duckdb.DuckDBPyConnection, tf: str = "h1") -> pd.DataFrame:
    bars = load_bars(con)
    feats = load_features(con)
    macro = load_macro(con)
    cot = load_cot(con)
    regimes = load_regimes(con)

    bars["ts"] = pd.to_datetime(bars["ts"])
    feats["ts"] = pd.to_datetime(feats["ts"])
    macro["ts"] = pd.to_datetime(macro["ts"])
    cot["ts"] = pd.to_datetime(cot["ts"])
    regimes["ts"] = pd.to_datetime(regimes["ts"])

    df = bars.copy()
    df = pd.merge_asof(df.sort_values("ts"), feats.sort_values("ts"),
                       on="ts", direction="backward")
    df = pd.merge_asof(df.sort_values("ts"), macro.sort_values("ts"),
                       on="ts", direction="backward")
    df = pd.merge_asof(df.sort_values("ts"), cot.sort_values("ts"),
                       on="ts", direction="backward")
    df = pd.merge_asof(df.sort_values("ts"), regimes.sort_values("ts"),
                       on="ts", direction="backward")
    return df.reset_index(drop=True)
