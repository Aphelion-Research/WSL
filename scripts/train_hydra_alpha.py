#!/usr/bin/env python3
"""HYDRA Alpha Model — Microstructure + Cross-Asset Lead-Lag + Regime Filtering.

Three alpha sources combined:
A) Microstructure features (from existing M5 data: volume dynamics, spread,
   price action microstructure, tick intensity proxies)
B) Cross-asset lead-lag (DXY/currencies/metals/equities predicting gold)
C) Regime classification (vol/trend/session regimes → trade only in favorable)

Architecture:
    1. Engineer 200+ new alpha features from existing data
    2. Train regime classifier (predict regime, not direction)
    3. Train direction model ONLY on favorable-regime bars
    4. Final model: regime gate → direction signal → confidence threshold
    5. Evaluate on raw accuracy AND on gated (tradeable) accuracy

Key insight: Don't predict direction on ALL bars. Predict WHICH bars are tradeable,
then predict direction ONLY on those. This is how real quant funds work.
"""
import json
import time
import pickle
import warnings
from pathlib import Path
from datetime import datetime

import numpy as np
import polars as pl
import lightgbm as lgb
from sklearn.metrics import (
    accuracy_score, f1_score, precision_score, recall_score,
    roc_auc_score, log_loss, classification_report
)
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

warnings.filterwarnings("ignore")
console = Console()

OUTPUT_DIR = Path("./output_hydra_alpha")
OUTPUT_DIR.mkdir(exist_ok=True)


# ═══════════════════════════════════════════════════════════════════
# A) MICROSTRUCTURE FEATURE ENGINEERING
# ═══════════════════════════════════════════════════════════════════

def engineer_microstructure_features(df: pl.DataFrame) -> pl.DataFrame:
    """Engineer microstructure features from existing M5 feature columns.

    Dataset has: close_in_range, upper_shad_pct, lower_shad_pct, body_pct,
    body_to_range, pin_bar, doji, inside_bar, engulf_*, streaks, vol_ratio_*,
    atr_*, parkinson_*, etc. We derive interaction/derivative features.
    """
    console.print("  [A] Engineering microstructure features...")

    exprs = []

    # --- Volatility compression/expansion (breakout predictor) ---
    # ATR ratio short/long = compression signal
    if "atr_5b" in df.columns and "atr_55b" in df.columns:
        exprs.append((pl.col("atr_5b") / pl.col("atr_55b").clip(lower_bound=0.0001)).alias("micro_atr_ratio_5_55"))
    if "atr_14b" in df.columns and "atr_144b" in df.columns:
        exprs.append((pl.col("atr_14b") / pl.col("atr_144b").clip(lower_bound=0.0001)).alias("micro_atr_ratio_14_144"))
    if "atr_5b" in df.columns and "atr_14b" in df.columns:
        exprs.append((pl.col("atr_5b") / pl.col("atr_14b").clip(lower_bound=0.0001)).alias("micro_atr_ratio_5_14"))

    # ATR acceleration (change in volatility)
    if "atr_14b" in df.columns:
        exprs.append(pl.col("atr_14b").diff(1).alias("micro_atr_accel"))
        exprs.append(pl.col("atr_14b").diff(5).alias("micro_atr_accel_5"))
        exprs.append(pl.col("atr_14b").pct_change(5).alias("micro_atr_pct_chg_5"))

    # Parkinson vol ratio (short/long = regime shift)
    if "parkinson_5b" in df.columns and "parkinson_55b" in df.columns:
        exprs.append((pl.col("parkinson_5b") / pl.col("parkinson_55b").clip(lower_bound=0.0001)).alias("micro_park_ratio_5_55"))
    if "parkinson_14b" in df.columns and "parkinson_72b" in df.columns:
        exprs.append((pl.col("parkinson_14b") / pl.col("parkinson_72b").clip(lower_bound=0.0001)).alias("micro_park_ratio_14_72"))

    # --- Volume microstructure ---
    vol_5 = pl.col("vol_ratio_5b")
    vol_20 = pl.col("vol_ratio_20b")
    vol_60 = pl.col("vol_ratio_60b")

    # Volume acceleration
    exprs.append(vol_20.diff(1).alias("micro_vol_accel"))
    exprs.append(vol_20.diff(1).diff(1).alias("micro_vol_jerk"))
    exprs.append(vol_5.diff(1).alias("micro_vol5_accel"))

    # Volume trend (5-bar vs 60-bar)
    exprs.append((vol_5 / vol_60.clip(lower_bound=0.01)).alias("micro_vol_trend"))

    # Abnormal volume persistence
    abnormal = pl.col("abnormal_vol")
    for w in [3, 5, 10, 20]:
        exprs.append(abnormal.rolling_sum(w).alias(f"micro_abnormal_persist_{w}"))
        exprs.append(abnormal.rolling_mean(w).alias(f"micro_abnormal_ma_{w}"))

    # Vol × direction interaction (volume confirms move?)
    if "pct_ret_1b" in df.columns:
        ret = pl.col("pct_ret_1b")
        exprs.append((ret * vol_5).alias("micro_vol_dir_confirm"))
        exprs.append((ret.abs() / vol_5.clip(lower_bound=0.01)).alias("micro_move_per_vol"))

    # --- Price action patterns (interactions) ---
    # Signed conviction: body_to_range × direction
    if "body_to_range" in df.columns and "pct_ret_1b" in df.columns:
        exprs.append((pl.col("body_to_range") * pl.col("pct_ret_1b").sign()).alias("micro_signed_conviction"))

    # Shadow imbalance (buying vs selling pressure)
    if "upper_shad_pct" in df.columns and "lower_shad_pct" in df.columns:
        exprs.append((pl.col("lower_shad_pct") - pl.col("upper_shad_pct")).alias("micro_shadow_imbalance"))
        # Rolling shadow imbalance (persistent rejection)
        shadow_imb = pl.col("lower_shad_pct") - pl.col("upper_shad_pct")
        for w in [5, 14]:
            exprs.append(shadow_imb.rolling_mean(w).alias(f"micro_shadow_imb_ma_{w}"))

    # Close position momentum
    if "close_in_range" in df.columns:
        cir = pl.col("close_in_range")
        exprs.append(cir.diff(1).alias("micro_cir_momentum"))
        exprs.append(cir.rolling_mean(5).alias("micro_cir_ma5"))
        exprs.append(cir.rolling_mean(14).alias("micro_cir_ma14"))
        exprs.append((cir - cir.rolling_mean(20)).alias("micro_cir_deviation"))

    # Streak exhaustion (long streaks tend to reverse)
    if "bull_streak" in df.columns and "bear_streak" in df.columns:
        exprs.append((pl.col("bull_streak") - pl.col("bear_streak")).alias("micro_net_streak"))
        exprs.append((pl.col("bull_streak") + pl.col("bear_streak")).alias("micro_total_streak"))

    # Pattern clustering (multiple patterns = strong signal)
    pattern_cols = [c for c in df.columns if c in ("pin_bar", "doji", "inside_bar", "engulf_bull", "engulf_bear")]
    if len(pattern_cols) >= 2:
        pattern_sum = sum(pl.col(c) for c in pattern_cols)
        exprs.append(pattern_sum.alias("micro_pattern_count"))

    # --- RSI/Stoch divergence with price ---
    if "rsi_14b" in df.columns and "pct_ret_5b" in df.columns:
        # Price making new highs but RSI falling = bearish divergence
        rsi_chg = pl.col("rsi_14b").diff(5)
        price_chg = pl.col("pct_ret_5b")
        exprs.append((price_chg - rsi_chg / 100).alias("micro_rsi_divergence"))

    if "stoch_k_14" in df.columns:
        exprs.append(pl.col("stoch_k_14").diff(3).alias("micro_stoch_momentum"))

    # --- Time interactions ---
    if "sin_hour" in df.columns:
        exprs.append((pl.col("sin_hour") * vol_20).alias("micro_hour_vol_sin"))
        exprs.append((pl.col("cos_hour") * vol_20).alias("micro_hour_vol_cos"))
        if "atr_14b" in df.columns:
            exprs.append((pl.col("sin_hour") * pl.col("atr_14b")).alias("micro_hour_atr_sin"))

    df = df.with_columns(exprs)

    micro_cols = [c for c in df.columns if c.startswith("micro_")]
    console.print(f"    Created {len(micro_cols)} microstructure features")
    return df


# ═══════════════════════════════════════════════════════════════════
# B) CROSS-ASSET LEAD-LAG FEATURES
# ═══════════════════════════════════════════════════════════════════

def engineer_leadlag_features(df: pl.DataFrame) -> pl.DataFrame:
    """Engineer cross-asset lead-lag features.

    Key relationships for gold:
    - DXY inverse correlation (strongest)
    - US yields (inverse when real rates rise)
    - VIX (flight to safety)
    - Silver (co-movement, silver often leads)
    - Copper/oil (risk sentiment)
    - JPY crosses (safe haven proxy)

    We compute LAGGED cross-asset returns and their interaction with gold.
    The hypothesis: other markets move first, gold follows.
    """
    console.print("  [B] Engineering cross-asset lead-lag features...")

    exprs = []

    # Cross-asset momentum divergence
    # If silver rallied but gold hasn't caught up → gold will follow
    gold_ret_col = "pct_ret_1b" if "pct_ret_1b" in df.columns else "log_ret_1b"

    for pair in ["eurusd", "silver", "copper", "gbpusd", "dxy", "usdchf", "usdjpy"]:
        ret1d_col = f"{pair}_ret1d"
        ret5d_col = f"{pair}_ret5d"
        z20_col = f"{pair}_z20d"
        z60_col = f"{pair}_z60d"

        if ret1d_col in df.columns:
            # Relative momentum (pair vs gold)
            gold_ma = pl.col(gold_ret_col).rolling_mean(288)
            exprs.append(
                (pl.col(ret1d_col) - gold_ma).alias(f"lead_{pair}_vs_gold_1d")
            )
            # Lagged cross return (did it move yesterday → gold follows today?)
            exprs.append(pl.col(ret1d_col).shift(1).alias(f"lead_{pair}_lag1"))

        if ret5d_col in df.columns:
            exprs.append(pl.col(ret5d_col).alias(f"lead_{pair}_5d"))
            exprs.append(pl.col(ret5d_col).diff(1).alias(f"lead_{pair}_5d_accel"))

        # Z-score features (mean-reversion signals)
        if z20_col in df.columns:
            exprs.append(pl.col(z20_col).alias(f"lead_{pair}_z20"))
        if z60_col in df.columns:
            exprs.append(pl.col(z60_col).alias(f"lead_{pair}_z60"))

    # VIX-based features (fear/greed)
    vix_cols = [c for c in df.columns if c.startswith("vix")]
    for c in vix_cols:
        if c.endswith(("_ret1d", "_ret5d", "_z20d")):
            exprs.append(pl.col(c).alias(f"lead_{c}"))

    # SP500/Nasdaq as risk proxy
    for idx in ["sp500", "nasdaq"]:
        for suffix in ["_ret1d", "_ret5d", "_z20d"]:
            col = f"{idx}{suffix}"
            if col in df.columns:
                exprs.append(pl.col(col).alias(f"lead_{col}"))

    # Cross-correlation features (rolling correlation between gold and leaders)
    # Already have corr_ columns, add lagged versions
    corr_cols = [c for c in df.columns if c.startswith("corr_")]
    for c in corr_cols:
        # Change in correlation = regime shift
        exprs.append(pl.col(c).diff(5).alias(f"lead_{c}_chg5"))

    # Multi-asset momentum score: aggregate cross-asset signals
    # Positive = risk-on (bad for gold), Negative = risk-off (good for gold)
    risk_on_cols = []
    for pair in ["sp500_ret5d", "nasdaq_ret5d", "copper_ret5d"]:
        if pair in df.columns:
            risk_on_cols.append(pair)

    if risk_on_cols:
        risk_score = sum(pl.col(c) for c in risk_on_cols) / len(risk_on_cols)
        exprs.append(risk_score.alias("lead_risk_score"))

    # Safe haven flow: JPY + CHF + gold alignment
    safe_cols = []
    for pair in ["usdchf_ret1d", "gbpusd_ret1d"]:
        if pair in df.columns:
            safe_cols.append(pair)
    if safe_cols:
        safe_score = sum(pl.col(c) for c in safe_cols) / len(safe_cols)
        exprs.append(safe_score.alias("lead_safe_haven_score"))

    # DXY proxy (from EURUSD inverse) — strongest gold predictor
    if "eurusd_ret1d" in df.columns:
        # DXY ≈ -EURUSD
        dxy_proxy = -pl.col("eurusd_ret1d")
        exprs.append(dxy_proxy.alias("lead_dxy_proxy_1d"))

        if "eurusd_ret5d" in df.columns:
            exprs.append((-pl.col("eurusd_ret5d")).alias("lead_dxy_proxy_5d"))

    # Yield curve proxy (if TLT data exists)
    tlt_cols = [c for c in df.columns if "tlt" in c.lower()]
    for c in tlt_cols:
        exprs.append(pl.col(c).alias(f"lead_{c}"))

    if exprs:
        df = df.with_columns(exprs)

    lead_cols = [c for c in df.columns if c.startswith("lead_")]
    console.print(f"    Created {len(lead_cols)} lead-lag features")
    return df


# ═══════════════════════════════════════════════════════════════════
# C) REGIME CLASSIFICATION
# ═══════════════════════════════════════════════════════════════════

def engineer_regime_features(df: pl.DataFrame) -> pl.DataFrame:
    """Engineer regime detection features.

    Regimes where direction prediction is possible:
    - Trending (clear momentum → continuation signals work)
    - Post-breakout (volatility expansion → momentum follows)
    - Mean-reverting (range-bound → buy low, sell high)

    Regimes where prediction is hopeless:
    - Chop (no follow-through, whipsaw)
    - Event-driven (news spike, unpredictable)
    - Low liquidity (Asian session, holidays)
    """
    console.print("  [C] Engineering regime features...")

    exprs = []

    # --- Trend strength (from returns, no raw OHLC needed) ---
    if "pct_ret_1b" in df.columns:
        ret = pl.col("pct_ret_1b")
        abs_ret = ret.abs()
        for w in [20, 50, 100]:
            # Efficiency ratio: |cumulative return| / sum(|returns|)
            cum_ret = ret.rolling_sum(w).abs()
            total_move = abs_ret.rolling_sum(w)
            efficiency = cum_ret / total_move.clip(lower_bound=0.0001)
            exprs.append(efficiency.alias(f"regime_efficiency_{w}"))

    # Hurst exponent proxy (already in dataset)
    if "hurst_20b" in df.columns:
        exprs.append(pl.col("hurst_20b").alias("regime_hurst_20"))
    if "hurst_100b" in df.columns:
        exprs.append(pl.col("hurst_100b").alias("regime_hurst_100"))

    # --- Volatility regime ---
    # Vol of vol (stability of volatility)
    for base in ["realized_vol_14b", "realized_vol_55b"]:
        if base in df.columns:
            vol_of_vol = pl.col(base).rolling_std(20)
            exprs.append(vol_of_vol.alias(f"regime_vov_{base}"))

    # ATR percentile (is vol high or low relative to history)
    if "atr_14b" in df.columns:
        for w in [100, 500]:
            # Rolling rank approximation
            atr_mean = pl.col("atr_14b").rolling_mean(w)
            atr_std = pl.col("atr_14b").rolling_std(w)
            atr_z = (pl.col("atr_14b") - atr_mean) / atr_std.clip(lower_bound=0.0001)
            exprs.append(atr_z.alias(f"regime_atr_z_{w}"))

    # --- Mean-reversion vs momentum ---
    # Autocorrelation of returns (positive = trending, negative = mean-reverting)
    if "autocorr_1_20b" in df.columns:
        exprs.append(pl.col("autocorr_1_20b").alias("regime_autocorr_20"))
    if "autocorr_1_60b" in df.columns:
        exprs.append(pl.col("autocorr_1_60b").alias("regime_autocorr_60"))

    # --- Session/time regime ---
    # Trading session quality (London overlap is best)
    exprs.append(pl.col("sin_hour").alias("regime_hour_sin"))
    exprs.append(pl.col("cos_hour").alias("regime_hour_cos"))
    if "is_monday" in df.columns:
        exprs.append(pl.col("is_monday").alias("regime_monday"))
    if "is_friday" in df.columns:
        exprs.append(pl.col("is_friday").alias("regime_friday"))

    # --- Existing regime columns (already numeric) ---
    for regime_col in ["vix_regime", "vol_regime", "trend_regime"]:
        if regime_col in df.columns:
            exprs.append(pl.col(regime_col).alias(f"regime_{regime_col}_num"))

    if exprs:
        df = df.with_columns(exprs)

    regime_cols = [c for c in df.columns if c.startswith("regime_")]
    console.print(f"    Created {len(regime_cols)} regime features")
    return df


# ═══════════════════════════════════════════════════════════════════
# REGIME-GATED DIRECTION MODEL
# ═══════════════════════════════════════════════════════════════════

def create_tradeability_target(df: pl.DataFrame, target_col: str, window: int = 20) -> np.ndarray:
    """Create binary target: 1 = this bar was followed by a clear directional move.

    Uses forward cumulative absolute return from pct_ret columns.
    A bar is 'tradeable' if:
    - The label exists (not NaN)
    - Forward volatility is above median (enough movement to profit)

    This effectively filters out chop/noise bars.
    """
    y = df[target_col].to_numpy().astype(np.float32)

    # Use pct_ret_1b to compute forward absolute return
    if "pct_ret_1b" in df.columns:
        ret = df["pct_ret_1b"].to_numpy().astype(np.float64)
    else:
        ret = df["log_ret_1b"].to_numpy().astype(np.float64)

    # Forward cumulative absolute return over window bars
    fwd_ret = np.zeros(len(ret), dtype=np.float64)
    abs_ret = np.abs(np.nan_to_num(ret, 0.0))
    # Rolling sum shifted forward
    cumsum = np.cumsum(abs_ret)
    for i in range(len(ret) - window):
        fwd_ret[i] = cumsum[i + window] - cumsum[i]
    fwd_ret[-(window):] = 0

    # Median forward return as threshold
    valid = np.isfinite(y)
    if valid.sum() > 0:
        median_fwd = np.median(fwd_ret[valid])
    else:
        median_fwd = 0.001

    # Tradeable = label exists AND forward move was above median
    tradeable = valid & (fwd_ret > median_fwd)
    return tradeable.astype(np.int32)


# ═══════════════════════════════════════════════════════════════════
# TRAINING PIPELINE
# ═══════════════════════════════════════════════════════════════════

def main():
    total_start = time.time()

    console.print(Panel.fit(
        "[bold]HYDRA ALPHA MODEL[/bold]\n"
        "A) Microstructure  B) Lead-Lag  C) Regime Gate\n"
        "Target: AUC 0.65+ on gated trades",
        style="bold green"
    ))

    # ═══ LOAD ═══
    console.print("\n[bold cyan]═══ LOAD ═══[/bold cyan]")
    df = pl.read_parquet("data/hydra_xauusd_m5_master_clean.parquet")
    console.print(f"  {df.shape[0]:,} rows x {df.shape[1]:,} cols")

    # ═══ FEATURE ENGINEERING ═══
    console.print("\n[bold cyan]═══ FEATURE ENGINEERING ═══[/bold cyan]")
    df = engineer_microstructure_features(df)
    df = engineer_leadlag_features(df)
    df = engineer_regime_features(df)

    # Collect all feature groups
    original_features = [c for c in df.columns if c not in
        {"time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"}
        and "label" not in c and "fwd" not in c]
    micro_features = [c for c in df.columns if c.startswith("micro_")]
    lead_features = [c for c in df.columns if c.startswith("lead_")]
    regime_features = [c for c in df.columns if c.startswith("regime_")]
    all_features = list(set(original_features + micro_features + lead_features + regime_features))

    console.print(f"\n  Total features: {len(all_features)}")
    console.print(f"    Original: {len(original_features)}")
    console.print(f"    + Micro: {len(micro_features)}")
    console.print(f"    + Lead-lag: {len(lead_features)}")
    console.print(f"    + Regime: {len(regime_features)}")

    # ═══ PREP ═══
    console.print("\n[bold cyan]═══ PREP ═══[/bold cyan]")

    # Targets
    targets = {
        "scalp": "label_12b",
        "day": "label_72b",
        "swing": "label_288b",
    }
    unified_target = "label_72b"

    # Drop rows where unified target is null
    df_clean = df.drop_nulls(subset=[unified_target])
    df_clean = df_clean.sort("time")
    df_clean = df_clean.with_columns([pl.col(c).fill_null(0.0) for c in all_features])

    # Replace inf — clip numeric columns
    float_features = [c for c in all_features if df_clean[c].dtype in (pl.Float32, pl.Float64)]
    df_clean = df_clean.with_columns([
        pl.col(c).clip(-1e6, 1e6) for c in float_features
    ])

    n = df_clean.shape[0]
    console.print(f"  Clean samples: {n:,}")

    X = df_clean.select(all_features).to_numpy().astype(np.float32)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

    y_unified = df_clean[unified_target].to_numpy().astype(np.int32)
    console.print(f"  Target dist: {dict(zip(*np.unique(y_unified, return_counts=True)))}")

    # Create tradeability target
    console.print("\n[bold cyan]═══ TRADEABILITY TARGET ═══[/bold cyan]")
    tradeable = create_tradeability_target(df_clean, unified_target, window=72)
    console.print(f"  Tradeable bars: {tradeable.sum():,} / {n:,} ({tradeable.mean():.1%})")

    # ═══ TEMPORAL SPLIT ═══
    console.print("\n[bold cyan]═══ TEMPORAL SPLIT (60/20/20) ═══[/bold cyan]")
    train_end = int(0.60 * n)
    val_end = int(0.80 * n)

    train_idx = np.arange(0, train_end)
    val_idx = np.arange(train_end, val_end)
    oos_idx = np.arange(val_end, n)

    console.print(f"  Train: {len(train_idx):,} | Val: {len(val_idx):,} | OOS: {len(oos_idx):,}")

    # ═══ MODEL 1: REGIME GATE (predict tradeability) ═══
    console.print("\n[bold red]═══ MODEL 1: REGIME GATE ═══[/bold red]")
    console.print("  Predicting which bars are tradeable...")

    # Use regime + micro features for gate
    gate_features = regime_features + micro_features + [c for c in all_features if "vol" in c or "atr" in c]
    gate_features = [c for c in gate_features if c in all_features]
    gate_feature_idx = [all_features.index(c) for c in gate_features if c in all_features]

    X_gate = X[:, gate_feature_idx]

    gate_params = {
        "objective": "binary", "metric": "auc",
        "boosting_type": "gbdt", "learning_rate": 0.03,
        "num_leaves": 63, "min_data_in_leaf": 200,
        "feature_fraction": 0.7, "bagging_fraction": 0.8,
        "bagging_freq": 5, "lambda_l1": 0.5, "lambda_l2": 2.0,
        "verbose": -1, "n_jobs": -1,
    }

    gate_train = lgb.Dataset(X_gate[train_idx], label=tradeable[train_idx])
    gate_val = lgb.Dataset(X_gate[val_idx], label=tradeable[val_idx], reference=gate_train)

    gate_model = lgb.train(
        gate_params, gate_train, num_boost_round=2000,
        valid_sets=[gate_train, gate_val], valid_names=["train", "val"],
        callbacks=[lgb.early_stopping(100, verbose=False), lgb.log_evaluation(200)],
    )

    gate_proba_oos = gate_model.predict(X_gate[oos_idx])
    gate_auc = roc_auc_score(tradeable[oos_idx], gate_proba_oos)
    console.print(f"  Gate OOS AUC: {gate_auc:.4f}")
    console.print(f"  Gate best iter: {gate_model.best_iteration}")

    # ═══ MODEL 2: DIRECTION (3 brains) ═══
    console.print("\n[bold red]═══ MODEL 2: DIRECTION BRAINS ═══[/bold red]")

    brain_models = {}
    brain_probas_oos = {}
    brain_probas_val = {}

    for brain_name, target_col in targets.items():
        console.print(f"\n  [bold yellow]── {brain_name.upper()} ({target_col}) ──[/bold yellow]")

        if target_col not in df_clean.columns:
            console.print(f"    [red]Target {target_col} missing, skip[/red]")
            continue

        y_brain = df_clean[target_col].fill_null(0).to_numpy().astype(np.int32)

        # Use ALL features for direction prediction
        brain_params = {
            "objective": "binary", "metric": "auc",
            "boosting_type": "gbdt", "learning_rate": 0.02,
            "num_leaves": 127, "min_data_in_leaf": 100,
            "feature_fraction": 0.5, "bagging_fraction": 0.7,
            "bagging_freq": 5, "lambda_l1": 0.3, "lambda_l2": 2.0,
            "verbose": -1, "n_jobs": -1,
        }

        d_train = lgb.Dataset(X[train_idx], label=y_brain[train_idx])
        d_val = lgb.Dataset(X[val_idx], label=y_brain[val_idx], reference=d_train)

        model = lgb.train(
            brain_params, d_train, num_boost_round=3000,
            valid_sets=[d_train, d_val], valid_names=["train", "val"],
            callbacks=[lgb.early_stopping(100, verbose=False), lgb.log_evaluation(500)],
        )

        proba_val = model.predict(X[val_idx])
        proba_oos = model.predict(X[oos_idx])

        auc_val = roc_auc_score(y_brain[val_idx], proba_val)
        auc_oos = roc_auc_score(y_brain[oos_idx], proba_oos)

        console.print(f"    Val AUC: {auc_val:.4f} | OOS AUC: {auc_oos:.4f} | Best iter: {model.best_iteration}")

        brain_models[brain_name] = model
        brain_probas_oos[brain_name] = proba_oos
        brain_probas_val[brain_name] = proba_val

    # ═══ MODEL 3: META-STACKER ═══
    console.print("\n[bold red]═══ MODEL 3: META-STACKER ═══[/bold red]")

    # Stack features: brain probas + gate proba + disagreement + top raw features
    gate_proba_val = gate_model.predict(X_gate[val_idx])
    gate_proba_full_oos = gate_model.predict(X_gate[oos_idx])

    stack_val = np.column_stack([
        *[brain_probas_val[b] for b in brain_models],
        gate_proba_val,
        np.std([brain_probas_val[b] for b in brain_models], axis=0),  # disagreement
    ])

    stack_oos = np.column_stack([
        *[brain_probas_oos[b] for b in brain_models],
        gate_proba_full_oos,
        np.std([brain_probas_oos[b] for b in brain_models], axis=0),
    ])

    # Train meta on val, evaluate on OOS
    # Split val into meta-train and meta-val
    meta_split = int(0.5 * len(val_idx))
    meta_train_idx = np.arange(0, meta_split)
    meta_val_idx = np.arange(meta_split, len(val_idx))

    meta_params = {
        "objective": "binary", "metric": "auc",
        "boosting_type": "gbdt", "learning_rate": 0.01,
        "num_leaves": 15, "min_data_in_leaf": 500,
        "feature_fraction": 0.9, "bagging_fraction": 0.9,
        "bagging_freq": 3, "lambda_l1": 2.0, "lambda_l2": 10.0,
        "verbose": -1,
    }

    y_val_unified = y_unified[val_idx]
    meta_d_train = lgb.Dataset(stack_val[meta_train_idx], label=y_val_unified[meta_train_idx])
    meta_d_val = lgb.Dataset(stack_val[meta_val_idx], label=y_val_unified[meta_val_idx], reference=meta_d_train)

    meta_model = lgb.train(
        meta_params, meta_d_train, num_boost_round=1000,
        valid_sets=[meta_d_train, meta_d_val], valid_names=["train", "val"],
        callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(100)],
    )

    meta_proba_oos = meta_model.predict(stack_oos)
    meta_auc_oos = roc_auc_score(y_unified[oos_idx], meta_proba_oos)
    console.print(f"  Meta OOS AUC: {meta_auc_oos:.4f}")

    # ═══ REGIME-GATED EVALUATION ═══
    console.print("\n[bold green]═══ REGIME-GATED EVALUATION ═══[/bold green]")
    console.print("  Only evaluating on bars the gate model deems tradeable...")

    y_oos = y_unified[oos_idx]

    # Test various gate thresholds
    gate_results = {}
    for gate_thresh in [0.3, 0.4, 0.5, 0.6, 0.7]:
        tradeable_mask = gate_proba_full_oos > gate_thresh
        n_tradeable = tradeable_mask.sum()

        if n_tradeable < 50:
            continue

        # Direction predictions on gated bars
        y_gated = y_oos[tradeable_mask]
        proba_gated = meta_proba_oos[tradeable_mask]
        pred_gated = (proba_gated > 0.5).astype(int)

        gated_acc = accuracy_score(y_gated, pred_gated)
        gated_auc = roc_auc_score(y_gated, proba_gated)
        gated_f1 = f1_score(y_gated, pred_gated, average="binary")
        gated_prec = precision_score(y_gated, pred_gated, average="binary", zero_division=0)
        gated_rec = recall_score(y_gated, pred_gated, average="binary")

        gate_results[gate_thresh] = {
            "n_trades": int(n_tradeable),
            "trade_rate": float(n_tradeable / len(y_oos)),
            "accuracy": float(gated_acc),
            "auc_roc": float(gated_auc),
            "f1": float(gated_f1),
            "precision": float(gated_prec),
            "recall": float(gated_rec),
        }

        console.print(f"  Gate>{gate_thresh:.1f}: acc={gated_acc:.4f} auc={gated_auc:.4f} "
                     f"f1={gated_f1:.4f} trades={n_tradeable:,} ({n_tradeable/len(y_oos):.1%})")

    # Also test confidence gating on direction model itself
    console.print("\n  [bold]Direction confidence gating:[/bold]")
    conf_results = {}
    for conf_thresh in [0.55, 0.60, 0.65, 0.70]:
        high_conf = (meta_proba_oos > conf_thresh) | (meta_proba_oos < (1 - conf_thresh))
        if high_conf.sum() < 50:
            continue

        y_conf = y_oos[high_conf]
        proba_conf = meta_proba_oos[high_conf]
        pred_conf = (proba_conf > 0.5).astype(int)

        conf_acc = accuracy_score(y_conf, pred_conf)
        conf_auc = roc_auc_score(y_conf, proba_conf) if len(np.unique(y_conf)) > 1 else 0.5
        conf_results[conf_thresh] = {
            "n_trades": int(high_conf.sum()),
            "accuracy": float(conf_acc),
            "auc_roc": float(conf_auc),
        }
        console.print(f"  Conf>{conf_thresh:.2f}: acc={conf_acc:.4f} auc={conf_auc:.4f} "
                     f"trades={high_conf.sum():,}")

    # Combined: regime gate + confidence gate
    console.print("\n  [bold]Combined (regime + confidence) gating:[/bold]")
    combined_results = {}
    for gate_t in [0.4, 0.5, 0.6]:
        for conf_t in [0.55, 0.60]:
            regime_ok = gate_proba_full_oos > gate_t
            conf_ok = (meta_proba_oos > conf_t) | (meta_proba_oos < (1 - conf_t))
            combined = regime_ok & conf_ok

            if combined.sum() < 50:
                continue

            y_comb = y_oos[combined]
            proba_comb = meta_proba_oos[combined]
            pred_comb = (proba_comb > 0.5).astype(int)

            comb_acc = accuracy_score(y_comb, pred_comb)
            comb_auc = roc_auc_score(y_comb, proba_comb) if len(np.unique(y_comb)) > 1 else 0.5

            key = f"gate>{gate_t:.1f}+conf>{conf_t:.2f}"
            combined_results[key] = {
                "n_trades": int(combined.sum()),
                "trade_rate": float(combined.mean()),
                "accuracy": float(comb_acc),
                "auc_roc": float(comb_auc),
            }
            console.print(f"  {key}: acc={comb_acc:.4f} auc={comb_auc:.4f} "
                         f"trades={combined.sum():,} ({combined.mean():.1%})")

    # ═══ RESULTS TABLE ═══
    console.print("\n")
    table = Table(title="HYDRA ALPHA MODEL — FINAL RESULTS", box=box.DOUBLE_EDGE)
    table.add_column("Component", style="cyan")
    table.add_column("OOS AUC", style="magenta")
    table.add_column("Detail", style="green")

    # Individual brains
    for b in brain_models:
        auc = roc_auc_score(y_oos, brain_probas_oos[b])
        table.add_row(f"{b} brain", f"{auc:.4f}", targets[b])

    table.add_row("", "", "")
    table.add_row("Regime gate", f"{gate_auc:.4f}", f"Predicts tradeability")
    table.add_row("Meta-stacker", f"{meta_auc_oos:.4f}", "Stacked ensemble")
    table.add_row("", "", "")

    # Best gated results
    if gate_results:
        best_gate = max(gate_results.items(), key=lambda x: x[1]["auc_roc"])
        table.add_row(
            f"GATED (regime>{best_gate[0]:.1f})",
            f"{best_gate[1]['auc_roc']:.4f}",
            f"{best_gate[1]['n_trades']:,} trades ({best_gate[1]['trade_rate']:.0%})",
            style="bold yellow",
        )

    if combined_results:
        best_combined = max(combined_results.items(), key=lambda x: x[1]["auc_roc"])
        table.add_row(
            f"COMBINED ({best_combined[0]})",
            f"{best_combined[1]['auc_roc']:.4f}",
            f"{best_combined[1]['n_trades']:,} trades ({best_combined[1]['trade_rate']:.0%})",
            style="bold green",
        )

    console.print(table)

    # ═══ SAVE ═══
    console.print("\n[bold green]═══ SAVING ALPHA MODEL ═══[/bold green]")

    alpha_model = {
        "gate_model": gate_model,
        "gate_feature_idx": gate_feature_idx,
        "brain_models": brain_models,
        "meta_model": meta_model,
        "all_features": all_features,
        "targets": targets,
        "unified_target": unified_target,
    }

    model_path = OUTPUT_DIR / "hydra_alpha_model.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(alpha_model, f)

    total_time = time.time() - total_start

    results = {
        "timestamp": datetime.now().isoformat(),
        "total_time_s": total_time,
        "n_samples": n,
        "n_features": len(all_features),
        "n_micro_features": len(micro_features),
        "n_lead_features": len(lead_features),
        "n_regime_features": len(regime_features),
        "gate_auc": gate_auc,
        "meta_auc": meta_auc_oos,
        "brain_aucs": {b: float(roc_auc_score(y_oos, brain_probas_oos[b])) for b in brain_models},
        "gate_results": gate_results,
        "conf_results": conf_results,
        "combined_results": combined_results,
    }

    results_path = OUTPUT_DIR / "alpha_results.json"
    results_path.write_text(json.dumps(results, indent=2, default=str))

    console.print(f"  Model: {model_path}")
    console.print(f"  Results: {results_path}")
    console.print(f"  Time: {total_time:.0f}s")

    console.print(Panel.fit(
        f"[bold green]HYDRA ALPHA COMPLETE[/bold green]\n\n"
        f"Gate AUC: {gate_auc:.4f}\n"
        f"Meta AUC: {meta_auc_oos:.4f}\n"
        f"Best gated: {best_combined[1]['auc_roc']:.4f} ({best_combined[1]['n_trades']:,} trades)\n"
        f"Model: {model_path}",
        style="bold green"
    ))


if __name__ == "__main__":
    main()
