"""HYDRA global configuration — all hyperparameters, paths, constants."""
from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass

ROOT = Path.home() / "Dominion"
DB_PATH = ROOT / "data" / "dominion.duckdb"
ARTIFACTS = ROOT / "artifacts" / "hydra"
RAGD_URL = "http://127.0.0.1:7474"


@dataclass(frozen=True)
class TargetConfig:
    atr_window: int = 14
    stop_mult: float = 1.0
    target_mult: float = 2.0
    horizon_bars: int = 20
    min_atr_pct: float = 0.0005


@dataclass(frozen=True)
class CVConfig:
    n_splits: int = 6
    train_frac: float = 0.70
    val_frac: float = 0.15
    test_frac: float = 0.15
    purge_bars: int = 20
    embargo_bars: int = 10


@dataclass(frozen=True)
class FeatureConfig:
    mi_top_k: int = 200
    ic_min_abs: float = 0.015
    ic_window: int = 252
    add_esn: bool = True
    add_gat: bool = True
    add_causal: bool = True
    add_ragd_episodic: bool = True
    ragd_k: int = 10


@dataclass(frozen=True)
class EnsembleConfig:
    long_threshold: float = 0.60
    short_threshold: float = 0.40
    stack_signals_req: int = 5
    pe_max: float = 0.95
    bma_temp: float = 1.0


@dataclass(frozen=True)
class BacktestConfig:
    spread_pips: float = 0.30
    slippage_pips: float = 0.10
    commission_rt: float = 2.00
    pip_value: float = 1.00
    capital: float = 100_000.0
    kelly_frac: float = 0.25
    pos_cap: float = 0.25
    trailing_to_be_at: float = 1.0


@dataclass(frozen=True)
class StopConfig:
    sharpe_min: float = 2.0
    win_rate_min: float = 0.70
    rr_min: float = 2.0
    profit_min: float = 10_000.0
    dd_kill: float = 0.05
    edge_decay_win: int = 20
    edge_decay_wr: float = 0.45


TARGET = TargetConfig()
CV = CVConfig()
FEATURES = FeatureConfig()
ENSEMBLE = EnsembleConfig()
BACKTEST = BacktestConfig()
STOP = StopConfig()
