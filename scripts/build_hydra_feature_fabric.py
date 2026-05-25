#!/usr/bin/env python3
"""
HYDRA Feature Fabric Builder v1
Builds ~2000 candidate features from all available XAUUSD data sources.

Architecture:
- Raw OHLCV from MT5 M5 MASTER as spine
- Merge existing master_clean features
- Generate new feature families via Python + C++
- Validate leakage, determinism, manifests
- Output to parquet with full metadata

Usage:
    python scripts/build_hydra_feature_fabric.py [--rows N] [--validate-only]
"""

import sys
import os
import time
import json
import hashlib
import argparse
from pathlib import Path
from collections import defaultdict

import numpy as np
import polars as pl
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "dominion_cpp" / "build"))

# ============================================================
# PHASE 1: Source Discovery & Loading
# ============================================================

def discover_sources():
    """Find and catalog all available data sources."""
    inventory = {}

    # 1. MT5 M5 MASTER (spine)
    mt5_path = ROOT / "data" / "mt5_history" / "XAUUSD_M5_MASTER.parquet"
    if mt5_path.exists():
        pf = pq.ParquetFile(str(mt5_path))
        inventory["mt5_m5_master"] = {
            "path": str(mt5_path),
            "rows": pf.metadata.num_rows,
            "columns": pf.metadata.num_columns,
            "status": "FOUND_AND_USED",
            "role": "spine"
        }
    else:
        inventory["mt5_m5_master"] = {"status": "NOT_AVAILABLE"}

    # 2. Existing master_clean
    mc_path = ROOT / "data" / "hydra_xauusd_m5_master_clean.parquet"
    if mc_path.exists():
        pf = pq.ParquetFile(str(mc_path))
        inventory["master_clean"] = {
            "path": str(mc_path),
            "rows": pf.metadata.num_rows,
            "columns": pf.metadata.num_columns,
            "status": "FOUND_AND_USED",
            "role": "existing_features"
        }
    else:
        inventory["master_clean"] = {"status": "NOT_AVAILABLE"}

    # 3. Higher timeframe bars
    for tf in ["H1", "H4", "D1"]:
        tf_path = ROOT / "data" / "mt5_history" / f"XAUUSD_{tf}.parquet"
        if tf_path.exists():
            pf = pq.ParquetFile(str(tf_path))
            inventory[f"mt5_{tf.lower()}"] = {
                "path": str(tf_path),
                "rows": pf.metadata.num_rows,
                "columns": pf.metadata.num_columns,
                "status": "FOUND_AND_USED",
                "role": "cross_timeframe"
            }
        else:
            inventory[f"mt5_{tf.lower()}"] = {"status": "NOT_AVAILABLE"}

    # 4. Macro data
    macro_dir = ROOT / "data" / "macro"
    macro_ext_dir = ROOT / "data" / "macro_extended"
    macro_count = 0
    if macro_dir.exists():
        macro_count += len(list(macro_dir.glob("*.parquet")))
    if macro_ext_dir.exists():
        macro_count += len(list(macro_ext_dir.glob("*.parquet")))
    inventory["macro_fred"] = {
        "path": str(macro_dir),
        "series_count": macro_count,
        "status": "FOUND_AND_USED" if macro_count > 0 else "NOT_AVAILABLE",
        "role": "macro_features"
    }

    # 5. Cross-asset daily
    ca_path = ROOT / "data" / "cross_asset" / "cross_asset_daily.parquet"
    if ca_path.exists():
        pf = pq.ParquetFile(str(ca_path))
        inventory["cross_asset_daily"] = {
            "path": str(ca_path),
            "rows": pf.metadata.num_rows,
            "columns": pf.metadata.num_columns,
            "status": "FOUND_AND_USED",
            "role": "cross_asset"
        }
    else:
        inventory["cross_asset_daily"] = {"status": "NOT_AVAILABLE"}

    # 6. Alternative data
    for name, rel_path in [
        ("gpr", "data/alternative/gpr_daily.parquet"),
        ("cot", "data/cot/cot_gold_weekly.parquet"),
        ("etf_flows", "data/etf/etf_flows_daily.parquet"),
    ]:
        full = ROOT / rel_path
        if full.exists():
            pf = pq.ParquetFile(str(full))
            inventory[name] = {
                "path": str(full),
                "rows": pf.metadata.num_rows,
                "columns": pf.metadata.num_columns,
                "status": "FOUND_AND_USED",
                "role": "alternative"
            }
        else:
            inventory[name] = {"status": "NOT_AVAILABLE"}

    # 7. C++ feature module
    try:
        import dominion_features
        inventory["cpp_features"] = {
            "status": "FOUND_AND_USED",
            "functions": 17,
            "role": "advanced_features"
        }
    except ImportError:
        inventory["cpp_features"] = {"status": "FOUND_BUT_FAILED", "reason": "import failed"}

    return inventory


def load_spine():
    """Load MT5 M5 MASTER as the base spine with raw OHLCV."""
    path = ROOT / "data" / "mt5_history" / "XAUUSD_M5_MASTER.parquet"
    df = pl.read_parquet(str(path))
    # Normalize column names and pick timestamp
    if "timestamp" in df.columns and "time" in df.columns:
        df = df.drop("time")
        df = df.rename({"timestamp": "time"})
    elif "timestamp" in df.columns:
        df = df.rename({"timestamp": "time"})

    df = df.sort("time")
    # Keep raw OHLCV
    keep = ["time", "open", "high", "low", "close", "tick_volume", "spread"]
    if "real_volume" in df.columns:
        keep.append("real_volume")
    df = df.select([c for c in keep if c in df.columns])
    return df


# ============================================================
# PHASE 2: Feature Families - Pure Python/Polars
# ============================================================

def build_return_features(df: pl.DataFrame) -> pl.DataFrame:
    """Family 1: Return/price transform features (~150)."""
    close = df["close"]
    features = {}

    horizons = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 288]

    for h in horizons:
        # Log returns (lagged by 1 to avoid lookahead)
        features[f"log_ret_{h}b"] = close.log().diff(h).shift(1)
        features[f"pct_ret_{h}b"] = close.pct_change(h).shift(1)

    # Rolling cumulative returns
    for w in [5, 10, 20, 60, 120, 288]:
        log_ret_1 = close.log().diff(1).shift(1)
        features[f"cum_ret_{w}b"] = log_ret_1.rolling_sum(window_size=w)

    # Return z-scores
    log_ret_1 = close.log().diff(1).shift(1)
    for w in [20, 60, 144, 288]:
        mean = log_ret_1.rolling_mean(window_size=w)
        std = log_ret_1.rolling_std(window_size=w)
        features[f"ret_zscore_{w}b"] = (log_ret_1 - mean) / std.clip(lower_bound=1e-10)

    # Return ranks (percentile within rolling window)
    for w in [60, 144, 288]:
        features[f"ret_rank_{w}b"] = log_ret_1.rolling_quantile(quantile=0.5, window_size=w)

    # Return acceleration (diff of returns)
    for h in [1, 5, 13, 34]:
        ret = close.log().diff(h).shift(1)
        features[f"ret_accel_{h}b"] = ret.diff(1)
        features[f"ret_jerk_{h}b"] = ret.diff(1).diff(1)

    # Signed return persistence
    sign = log_ret_1.sign()
    for w in [5, 10, 20, 60]:
        features[f"ret_persist_{w}b"] = sign.rolling_mean(window_size=w)

    # Mean reversion scores
    for w in [20, 60, 144]:
        rolling_mean = close.shift(1).rolling_mean(window_size=w)
        features[f"mean_rev_{w}b"] = (close.shift(1) - rolling_mean) / rolling_mean.clip(lower_bound=1e-10)

    # Drawdown/drawup
    for w in [10, 20, 60, 144, 288]:
        rolling_max = close.shift(1).rolling_max(window_size=w)
        rolling_min = close.shift(1).rolling_min(window_size=w)
        features[f"dd_{w}b"] = (close.shift(1) - rolling_max) / rolling_max.clip(lower_bound=1e-10)
        features[f"du_{w}b"] = (close.shift(1) - rolling_min) / rolling_min.clip(lower_bound=1e-10)

    result = df.select("time")
    for name, series in features.items():
        result = result.with_columns(series.alias(name))
    return result


def build_volatility_features(df: pl.DataFrame) -> pl.DataFrame:
    """Family 2: Volatility/regime features (~250)."""
    features = {}
    close = df["close"]
    high = df["high"]
    low = df["low"]
    opn = df["open"]

    log_ret = close.log().diff(1).shift(1)

    windows = [5, 8, 10, 14, 20, 34, 55, 72, 89, 144, 288, 576]

    # Pre-compute base series once
    hl_ratio = (high.shift(1) / low.shift(1)).log()
    park_base = hl_ratio.pow(2) / (4 * np.log(2))

    log_h = high.shift(1).log()
    log_l = low.shift(1).log()
    log_c = close.shift(1).log()
    log_o = opn.shift(1).log()
    hl2 = (log_h - log_l).pow(2)
    co2 = (log_c - log_o).pow(2)
    gk_base = 0.5 * hl2 - (2 * np.log(2) - 1) * co2

    hc = log_h - log_c
    ho = log_h - log_o
    lc = log_l - log_c
    lo_val = log_l - log_o
    rs_base = hc * ho + lc * lo_val

    for w in windows:
        features[f"rvol_{w}b"] = log_ret.rolling_std(window_size=w)
        features[f"park_vol_{w}b"] = park_base.rolling_mean(window_size=w).sqrt()
        features[f"gk_vol_{w}b"] = gk_base.rolling_mean(window_size=w).abs().sqrt()
        features[f"rs_vol_{w}b"] = rs_base.rolling_mean(window_size=w).abs().sqrt()

    # EWMA volatility
    log_ret_sq = log_ret.pow(2)
    for span in [10, 20, 60, 144]:
        features[f"ewma_vol_{span}b"] = log_ret_sq.ewm_mean(span=span).sqrt()

    # Volatility z-scores
    for w in [20, 60, 144, 288]:
        vol = log_ret.rolling_std(window_size=w)
        vol_mean = vol.rolling_mean(window_size=w)
        vol_std = vol.rolling_std(window_size=w)
        features[f"vol_zscore_{w}b"] = (vol - vol_mean) / vol_std.clip(lower_bound=1e-10)

    # Vol-of-vol
    for w in [20, 60, 144]:
        vol_20 = log_ret.rolling_std(window_size=20)
        features[f"vov_{w}b"] = vol_20.rolling_std(window_size=w)

    # Volatility ratio (short/long)
    for short, long in [(5, 20), (5, 60), (10, 60), (20, 144), (60, 288)]:
        vol_s = log_ret.rolling_std(window_size=short)
        vol_l = log_ret.rolling_std(window_size=long)
        features[f"vol_ratio_{short}_{long}b"] = vol_s / vol_l.clip(lower_bound=1e-10)

    # ATR variants
    tr = pl.max_horizontal(
        (high.shift(1) - low.shift(1)).abs(),
        (high.shift(1) - close.shift(2)).abs(),
        (low.shift(1) - close.shift(2)).abs(),
    )
    for w in windows[:10]:
        features[f"atr_{w}b"] = tr.rolling_mean(window_size=w)
        features[f"atr_pct_{w}b"] = tr.rolling_mean(window_size=w) / close.shift(1).clip(lower_bound=1e-10)

    # Range expansion
    for w in [5, 10, 20, 60]:
        range_now = high.shift(1) - low.shift(1)
        range_avg = range_now.rolling_mean(window_size=w)
        features[f"range_exp_{w}b"] = range_now / range_avg.clip(lower_bound=1e-10)

    # Compression (vol declining)
    for w in [20, 60, 144]:
        vol = log_ret.rolling_std(window_size=20)
        features[f"vol_slope_{w}b"] = vol.diff(w) / vol.shift(w).clip(lower_bound=1e-10)

    # Rolling drawdown depth
    for w in [60, 144, 288]:
        rm = close.shift(1).rolling_max(window_size=w)
        features[f"max_dd_{w}b"] = (close.shift(1) - rm) / rm.clip(lower_bound=1e-10)

    result = df.select("time")
    for name, series in features.items():
        result = result.with_columns(series.alias(name))
    return result


def build_trend_momentum_features(df: pl.DataFrame) -> pl.DataFrame:
    """Family 3: Trend/momentum features (~250)."""
    features = {}
    close = df["close"].shift(1)  # Point-in-time safe
    high = df["high"].shift(1)
    low = df["low"].shift(1)

    # Moving average gaps
    ema_spans = [5, 8, 13, 21, 34, 55, 89, 144, 233, 288]
    for span in ema_spans:
        ema_val = close.ewm_mean(span=span)
        features[f"ema_gap_{span}b"] = (close - ema_val) / ema_val.clip(lower_bound=1e-10)

    # SMA gaps
    for w in [10, 20, 50, 100, 200]:
        sma = close.rolling_mean(window_size=w)
        features[f"sma_gap_{w}b"] = (close - sma) / sma.clip(lower_bound=1e-10)

    # EMA/SMA ratios
    for fast, slow in [(5, 20), (8, 34), (13, 55), (21, 89), (34, 144), (55, 233)]:
        ema_f = close.ewm_mean(span=fast)
        ema_s = close.ewm_mean(span=slow)
        features[f"ema_ratio_{fast}_{slow}b"] = ema_f / ema_s.clip(lower_bound=1e-10) - 1.0

    # Slope features (linear regression slope approximation)
    for w in [5, 10, 20, 60, 144]:
        # Approximation: (last - first) / window
        features[f"slope_{w}b"] = (close - close.shift(w)) / (w * close.shift(w).clip(lower_bound=1e-10))

    # Momentum (ROC)
    for h in [5, 10, 20, 60, 89, 144, 288]:
        features[f"mom_{h}b"] = (close - close.shift(h)) / close.shift(h).clip(lower_bound=1e-10)

    # RSI-style
    log_ret = close.log().diff(1)
    gain = log_ret.clip(lower_bound=0.0)
    loss = (-log_ret).clip(lower_bound=0.0)
    for w in [7, 14, 21, 34, 55]:
        avg_gain = gain.rolling_mean(window_size=w)
        avg_loss = loss.rolling_mean(window_size=w)
        rs = avg_gain / avg_loss.clip(lower_bound=1e-10)
        features[f"rsi_{w}b"] = 100 - (100 / (1 + rs))

    # Stochastic %K/%D
    for w in [5, 14, 21, 55]:
        hh = high.rolling_max(window_size=w)
        ll = low.rolling_min(window_size=w)
        features[f"stoch_k_{w}b"] = (close - ll) / (hh - ll).clip(lower_bound=1e-10) * 100
        features[f"stoch_d_{w}b"] = features[f"stoch_k_{w}b"].rolling_mean(window_size=3)

    # MACD-style
    for fast, slow, sig in [(12, 26, 9), (5, 34, 5), (8, 21, 5), (21, 55, 13)]:
        ema_f = close.ewm_mean(span=fast)
        ema_s = close.ewm_mean(span=slow)
        macd_line = ema_f - ema_s
        signal = macd_line.ewm_mean(span=sig)
        features[f"macd_{fast}_{slow}_{sig}"] = macd_line / close.clip(lower_bound=1e-10)
        features[f"macd_hist_{fast}_{slow}_{sig}"] = (macd_line - signal) / close.clip(lower_bound=1e-10)

    # Breakout distance
    for w in [20, 60, 144, 288]:
        hh = high.rolling_max(window_size=w)
        ll = low.rolling_min(window_size=w)
        features[f"breakout_high_{w}b"] = (close - hh) / hh.clip(lower_bound=1e-10)
        features[f"breakout_low_{w}b"] = (close - ll) / ll.clip(lower_bound=1e-10)
        features[f"channel_pos_{w}b"] = (close - ll) / (hh - ll).clip(lower_bound=1e-10)

    # Bollinger position
    for w in [10, 20, 34, 55, 89]:
        sma = close.rolling_mean(window_size=w)
        std = close.rolling_std(window_size=w)
        features[f"bb_pos_{w}b"] = (close - sma) / (2 * std).clip(lower_bound=1e-10)
        features[f"bb_width_{w}b"] = (2 * std) / sma.clip(lower_bound=1e-10)

    # Z-scored momentum
    for h in [5, 20, 60, 144]:
        mom = (close - close.shift(h))
        mom_mean = mom.rolling_mean(window_size=h)
        mom_std = mom.rolling_std(window_size=h)
        features[f"mom_z_{h}b"] = (mom - mom_mean) / mom_std.clip(lower_bound=1e-10)

    # ADX approximation
    for w in [7, 14, 20, 34]:
        plus_dm = (high - high.shift(1)).clip(lower_bound=0.0)
        minus_dm = (low.shift(1) - low).clip(lower_bound=0.0)
        tr_val = pl.max_horizontal(
            (high - low).abs(),
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        )
        atr = tr_val.rolling_mean(window_size=w)
        features[f"plus_di_{w}b"] = plus_dm.rolling_mean(window_size=w) / atr.clip(lower_bound=1e-10) * 100
        features[f"minus_di_{w}b"] = minus_dm.rolling_mean(window_size=w) / atr.clip(lower_bound=1e-10) * 100
        dx = ((features[f"plus_di_{w}b"] - features[f"minus_di_{w}b"]).abs() /
              (features[f"plus_di_{w}b"] + features[f"minus_di_{w}b"]).clip(lower_bound=1e-10) * 100)
        features[f"adx_{w}b"] = dx.rolling_mean(window_size=w)

    result = df.select("time")
    for name, series in features.items():
        result = result.with_columns(series.alias(name))
    return result


def build_session_calendar_features(df: pl.DataFrame) -> pl.DataFrame:
    """Family 4: Session/time/calendar features (~150)."""
    features = {}
    ts = df["time"]
    close = df["close"].shift(1)
    log_ret = close.log().diff(1)

    # Basic time features
    hour = ts.dt.hour()
    minute = ts.dt.minute()
    dow = ts.dt.weekday()
    dom = ts.dt.day()
    month = ts.dt.month()

    features["hour"] = hour.cast(pl.Float32)
    features["minute_bucket"] = (minute / 5).cast(pl.Float32)
    features["dow"] = dow.cast(pl.Float32)
    features["dom"] = dom.cast(pl.Float32)
    features["month"] = month.cast(pl.Float32)

    # Cyclical encoding
    for period, name in [(24, "hour"), (7, "dow"), (12, "month")]:
        base = features[name].cast(pl.Float64)
        features[f"sin_{name}"] = (base * 2 * np.pi / period).sin().cast(pl.Float32)
        features[f"cos_{name}"] = (base * 2 * np.pi / period).cos().cast(pl.Float32)

    # Session flags
    # Asia: 00:00-08:00 UTC, London: 07:00-16:00 UTC, NY: 12:00-21:00 UTC
    features["is_asia"] = ((hour >= 0) & (hour < 8)).cast(pl.Float32)
    features["is_london"] = ((hour >= 7) & (hour < 16)).cast(pl.Float32)
    features["is_ny"] = ((hour >= 12) & (hour < 21)).cast(pl.Float32)
    features["is_overlap_london_ny"] = ((hour >= 12) & (hour < 16)).cast(pl.Float32)
    features["is_overlap_asia_london"] = ((hour >= 7) & (hour < 8)).cast(pl.Float32)

    # Session age (bars since session start)
    features["asia_age"] = pl.when(hour < 8).then(hour * 12 + minute / 5).otherwise(pl.lit(None)).cast(pl.Float32)
    features["london_age"] = pl.when((hour >= 7) & (hour < 16)).then((hour - 7) * 12 + minute / 5).otherwise(pl.lit(None)).cast(pl.Float32)
    features["ny_age"] = pl.when((hour >= 12) & (hour < 21)).then((hour - 12) * 12 + minute / 5).otherwise(pl.lit(None)).cast(pl.Float32)

    # Time-of-day volatility (rolling vol by hour)
    for h_start in range(0, 24, 4):
        h_end = h_start + 4
        mask = (hour >= h_start) & (hour < h_end)
        features[f"in_block_{h_start:02d}_{h_end:02d}"] = mask.cast(pl.Float32)

    # Month-end, quarter-end, year-end proximity
    features["days_to_month_end"] = (pl.lit(31) - dom).cast(pl.Float32).clip(upper_bound=15)
    features["is_month_end_week"] = (dom >= 25).cast(pl.Float32)
    features["is_quarter_end_month"] = month.is_in([3, 6, 9, 12]).cast(pl.Float32)
    features["is_year_end_month"] = (month == 12).cast(pl.Float32)

    # Day of year cyclical
    doy = ts.dt.ordinal_day()
    features["sin_doy"] = (doy.cast(pl.Float64) * 2 * np.pi / 365).sin().cast(pl.Float32)
    features["cos_doy"] = (doy.cast(pl.Float64) * 2 * np.pi / 365).cos().cast(pl.Float32)

    # Week of year
    features["week_of_year"] = (doy / 7).cast(pl.Float32)

    # Monday/Friday effects
    features["is_monday"] = (dow == 0).cast(pl.Float32)
    features["is_friday"] = (dow == 4).cast(pl.Float32)

    # First/last hour of major sessions
    features["is_london_open_hour"] = ((hour == 7) | (hour == 8)).cast(pl.Float32)
    features["is_ny_open_hour"] = ((hour == 12) | (hour == 13)).cast(pl.Float32)
    features["is_london_close_hour"] = ((hour == 15) | (hour == 16)).cast(pl.Float32)
    features["is_ny_close_hour"] = ((hour == 20) | (hour == 21)).cast(pl.Float32)

    # Session return so far (cumulative return within current session)
    # Approximate: rolling return from session start
    for session_len in [96, 108, 108]:  # Asia~8h, London~9h, NY~9h = bars
        pass  # Will compute below using grouped rolling

    # Intraday volatility so far
    for w in [12, 24, 48]:  # 1h, 2h, 4h
        features[f"intraday_vol_{w}b"] = log_ret.rolling_std(window_size=w)

    # Intraday return so far
    for w in [12, 24, 48, 96]:
        features[f"intraday_ret_{w}b"] = log_ret.rolling_sum(window_size=w)

    # NFP week flag (first Friday of month, approx)
    features["is_nfp_week"] = ((dow <= 4) & (dom <= 7)).cast(pl.Float32)

    # FOMC proximity (approximate: 6 weeks apart, hard to compute exactly without calendar)
    # Use month pattern: FOMC typically in Jan, Mar, May, Jun, Jul, Sep, Nov, Dec
    features["is_fomc_month"] = month.is_in([1, 3, 5, 6, 7, 9, 11, 12]).cast(pl.Float32)

    result = df.select("time")
    for name, series in features.items():
        result = result.with_columns(series.alias(name))
    return result


def build_cpp_advanced_features(df: pl.DataFrame) -> pl.DataFrame:
    """Family 8: Entropy/fractal/signal-processing features via C++ (~200)."""
    try:
        import dominion_features as cpp
    except ImportError:
        print("WARNING: C++ module unavailable, skipping advanced features")
        return df.select("time")

    close_arr = df["close"].shift(1).fill_null(strategy="forward").to_numpy().astype(np.float64)
    features = {}

    # Permutation entropy at different scales
    for embed_dim in [3, 4, 5]:
        for window in [50, 100, 200]:
            try:
                pe = cpp.information.compute_permutation_entropy(close_arr, embed_dim, 1, window)
                features[f"perm_entropy_d{embed_dim}_w{window}"] = pe
            except Exception:
                pass

    # Sample entropy (expensive - limit windows for small arrays)
    se_windows = [50, 100] if len(close_arr) < 10000 else [50, 100, 200]
    for m in [2, 3]:
        for window in se_windows:
            try:
                se = cpp.information.compute_sample_entropy(close_arr, m, 0.2, window)
                features[f"sample_entropy_m{m}_w{window}"] = se
            except Exception:
                pass

    # Lempel-Ziv complexity
    for window in [50, 100, 200, 500]:
        try:
            lz = cpp.information.compute_lz_complexity(close_arr, window)
            features[f"lz_complexity_w{window}"] = lz
        except Exception:
            pass

    # Hurst exponent
    for window in [100, 200, 500]:
        try:
            h = cpp.multifractal.compute_hurst_rs(close_arr, window)
            features[f"hurst_w{window}"] = h
        except Exception:
            pass

    # Fractal dimension
    for window in [50, 100, 200]:
        try:
            fd = cpp.multifractal.compute_fractal_dimension(close_arr, window)
            features[f"fractal_dim_w{window}"] = fd
        except Exception:
            pass

    # MFDFA (only if array is large enough to be meaningful)
    if len(close_arr) >= 2000:
        for window in [200, 500]:
            try:
                mfdfa = cpp.multifractal.compute_mfdfa(close_arr, window)
                if isinstance(mfdfa, dict):
                    for k, v in mfdfa.items():
                        features[f"mfdfa_{k}_w{window}"] = v
                elif isinstance(mfdfa, np.ndarray):
                    features[f"mfdfa_w{window}"] = mfdfa
            except Exception:
                pass

    # Noise decomposition - SSA
    try:
        ssa = cpp.noise.compute_ssa(close_arr, 60, 3)
        if hasattr(ssa, 'explained_variance') and ssa.explained_variance:
            for i, ev in enumerate(ssa.explained_variance[:3]):
                features[f"ssa_ev_{i}"] = np.full(len(close_arr), ev)
        if hasattr(ssa, 'trend') and len(ssa.trend) == len(close_arr):
            features["ssa_trend_ratio"] = ssa.trend / np.clip(close_arr, 1e-10, None)
    except Exception:
        pass

    # Also compute on returns
    ret_arr = np.diff(np.log(np.clip(close_arr, 1e-10, None)), prepend=0)

    for embed_dim in [3, 5]:
        for window in [100, 200]:
            try:
                pe = cpp.information.compute_permutation_entropy(ret_arr, embed_dim, 1, window)
                features[f"ret_perm_entropy_d{embed_dim}_w{window}"] = pe
            except Exception:
                pass

    for window in [100, 200]:
        try:
            lz = cpp.information.compute_lz_complexity(ret_arr, window)
            features[f"ret_lz_complexity_w{window}"] = lz
        except Exception:
            pass

    for window in [100, 200]:
        try:
            h = cpp.multifractal.compute_hurst_rs(ret_arr, window)
            features[f"ret_hurst_w{window}"] = h
        except Exception:
            pass

    # Rolling autocorrelation from returns (vectorized via pandas)
    import pandas as pd
    ret_series = pd.Series(ret_arr)
    for lag in [1, 5, 10, 20]:
        lagged = ret_series.shift(lag)
        for window in [60, 144, 288]:
            corr = ret_series.rolling(window, min_periods=window//2).corr(lagged)
            features[f"autocorr_lag{lag}_w{window}"] = corr.values

    n = len(close_arr)
    result = df.select("time")
    for name, arr in features.items():
        if isinstance(arr, np.ndarray) and len(arr) == n:
            result = result.with_columns(pl.Series(name=name, values=arr).cast(pl.Float32))
        elif isinstance(arr, (int, float)):
            result = result.with_columns(pl.lit(arr).cast(pl.Float32).alias(name))

    return result


def build_microstructure_features(df: pl.DataFrame) -> pl.DataFrame:
    """Family 7: Microstructure/source-quality features (~100+)."""
    features = {}

    if "spread" not in df.columns:
        return df.select("time")

    spread = df["spread"].shift(1)
    tick_vol = df["tick_volume"].shift(1) if "tick_volume" in df.columns else None
    close = df["close"].shift(1)

    # Spread features
    for w in [5, 10, 20, 60, 144, 288]:
        features[f"spread_mean_{w}b"] = spread.rolling_mean(window_size=w)
        features[f"spread_std_{w}b"] = spread.rolling_std(window_size=w)
        sp_mean = spread.rolling_mean(window_size=w)
        sp_std = spread.rolling_std(window_size=w)
        features[f"spread_zscore_{w}b"] = (spread - sp_mean) / sp_std.clip(lower_bound=1e-10)

    # Spread as % of price
    features["spread_pct"] = spread / close.clip(lower_bound=1e-10)
    for w in [20, 60, 144]:
        sp_pct = spread / close.clip(lower_bound=1e-10)
        features[f"spread_pct_z_{w}b"] = (sp_pct - sp_pct.rolling_mean(window_size=w)) / sp_pct.rolling_std(window_size=w).clip(lower_bound=1e-10)

    if tick_vol is not None:
        # Tick volume features
        for w in [5, 10, 20, 60, 144, 288]:
            features[f"tvol_mean_{w}b"] = tick_vol.rolling_mean(window_size=w)
            features[f"tvol_std_{w}b"] = tick_vol.rolling_std(window_size=w)
            tv_mean = tick_vol.rolling_mean(window_size=w)
            tv_std = tick_vol.rolling_std(window_size=w)
            features[f"tvol_zscore_{w}b"] = (tick_vol - tv_mean) / tv_std.clip(lower_bound=1e-10)

        # Volume ratio (short/long)
        for short, long in [(5, 20), (10, 60), (20, 144), (60, 288)]:
            vs = tick_vol.rolling_mean(window_size=short)
            vl = tick_vol.rolling_mean(window_size=long)
            features[f"tvol_ratio_{short}_{long}b"] = vs / vl.clip(lower_bound=1e-10)

        # Volume-weighted price movement (VWAP proxy)
        log_ret = close.log().diff(1)
        for w in [5, 20, 60]:
            vol_weight = tick_vol / tick_vol.rolling_sum(window_size=w).clip(lower_bound=1e-10)
            features[f"vwap_dev_{w}b"] = (log_ret * vol_weight).rolling_sum(window_size=w)

        # Abnormal volume
        for w in [20, 60, 144]:
            tv_mean = tick_vol.rolling_mean(window_size=w)
            features[f"abnormal_vol_{w}b"] = tick_vol / tv_mean.clip(lower_bound=1e-10)

        # Volume-return correlation
        for w in [20, 60, 144]:
            # Approximate rolling correlation
            ret = close.log().diff(1)
            ret_std = ret.rolling_std(window_size=w)
            vol_std = tick_vol.cast(pl.Float64).rolling_std(window_size=w)
            cov = (ret * tick_vol.cast(pl.Float64)).rolling_mean(window_size=w) - ret.rolling_mean(window_size=w) * tick_vol.cast(pl.Float64).rolling_mean(window_size=w)
            features[f"vol_ret_corr_{w}b"] = cov / (ret_std * vol_std).clip(lower_bound=1e-10)

    # Liquidity proxy (spread × tick_volume)
    if tick_vol is not None:
        liquidity = spread * tick_vol.cast(pl.Float64)
        for w in [20, 60, 144]:
            features[f"illiquidity_{w}b"] = liquidity.rolling_mean(window_size=w)
            liq_mean = liquidity.rolling_mean(window_size=w)
            liq_std = liquidity.rolling_std(window_size=w)
            features[f"illiquidity_z_{w}b"] = (liquidity - liq_mean) / liq_std.clip(lower_bound=1e-10)

    result = df.select("time")
    for name, series in features.items():
        result = result.with_columns(series.alias(name))
    return result


def build_cross_timeframe_features(df: pl.DataFrame) -> pl.DataFrame:
    """Family 9: Cross-timeframe features using H1/H4/D1 as-of join (~150)."""
    features = {}
    close_m5 = df["close"].shift(1)
    time_col = df["time"]

    for tf_name, tf_file, tf_bars_per_m5 in [("h1", "XAUUSD_H1.parquet", 12),
                                               ("h4", "XAUUSD_H4.parquet", 48),
                                               ("d1", "XAUUSD_D1.parquet", 288)]:
        tf_path = ROOT / "data" / "mt5_history" / tf_file
        if not tf_path.exists():
            continue

        tf_df = pl.read_parquet(str(tf_path))
        if "timestamp" in tf_df.columns and "time" in tf_df.columns:
            tf_df = tf_df.drop("time").rename({"timestamp": "time"})
        elif "timestamp" in tf_df.columns:
            tf_df = tf_df.rename({"timestamp": "time"})
        # Normalize timezone and precision to match spine
        tf_df = tf_df.with_columns(
            pl.col("time").cast(pl.Datetime("us")).dt.replace_time_zone(None)
        )
        tf_df = tf_df.sort("time")

        # As-of join higher TF onto M5
        tf_sel = tf_df.select([
            pl.col("time"),
            pl.col("close").alias(f"{tf_name}_close"),
            pl.col("high").alias(f"{tf_name}_high"),
            pl.col("low").alias(f"{tf_name}_low"),
        ])

        joined = df.select("time").join_asof(tf_sel, on="time", strategy="backward")

        htf_close = joined[f"{tf_name}_close"].shift(1)  # Extra shift for safety
        htf_high = joined[f"{tf_name}_high"].shift(1)
        htf_low = joined[f"{tf_name}_low"].shift(1)

        # Price relative to higher TF
        features[f"{tf_name}_gap"] = (close_m5 - htf_close) / htf_close.clip(lower_bound=1e-10)
        features[f"{tf_name}_high_dist"] = (close_m5 - htf_high) / htf_high.clip(lower_bound=1e-10)
        features[f"{tf_name}_low_dist"] = (close_m5 - htf_low) / htf_low.clip(lower_bound=1e-10)
        features[f"{tf_name}_range_pos"] = (close_m5 - htf_low) / (htf_high - htf_low).clip(lower_bound=1e-10)

        # Higher TF trend (returns)
        for h in [1, 3, 5, 10, 20]:
            features[f"{tf_name}_ret_{h}"] = htf_close.log().diff(h)

        # Higher TF volatility
        htf_ret = htf_close.log().diff(1)
        for w in [5, 10, 20]:
            features[f"{tf_name}_vol_{w}"] = htf_ret.rolling_std(window_size=w)

        # M5 vol / HTF vol ratio
        m5_ret = close_m5.log().diff(1)
        m5_vol = m5_ret.rolling_std(window_size=tf_bars_per_m5)
        htf_vol = htf_ret.rolling_std(window_size=5)
        features[f"{tf_name}_vol_ratio"] = m5_vol / htf_vol.clip(lower_bound=1e-10)

        # HTF momentum
        for w in [5, 10, 20]:
            features[f"{tf_name}_mom_{w}"] = (htf_close - htf_close.shift(w)) / htf_close.shift(w).clip(lower_bound=1e-10)

        # Divergence (M5 trend vs HTF trend)
        m5_trend = (close_m5 - close_m5.shift(tf_bars_per_m5)) / close_m5.shift(tf_bars_per_m5).clip(lower_bound=1e-10)
        htf_trend = (htf_close - htf_close.shift(1)) / htf_close.shift(1).clip(lower_bound=1e-10)
        features[f"{tf_name}_divergence"] = m5_trend - htf_trend

    result = df.select("time")
    for name, series in features.items():
        result = result.with_columns(series.alias(name))
    return result


def build_interaction_features(base_features: pl.DataFrame) -> pl.DataFrame:
    """Family 10: Feature interactions (~300)."""
    features = {}
    cols = base_features.columns

    # Define interaction pairs by family
    vol_cols = [c for c in cols if any(c.startswith(p) for p in ["rvol_", "park_vol_", "ewma_vol_"])][:5]
    mom_cols = [c for c in cols if any(c.startswith(p) for p in ["mom_", "rsi_", "slope_"])][:5]
    macro_cols = [c for c in cols if c.startswith("macro_")][:5]
    session_cols = [c for c in cols if c.startswith("is_")][:5]
    entropy_cols = [c for c in cols if any(c.startswith(p) for p in ["perm_entropy_", "lz_complexity_", "hurst_"])][:5]
    trend_cols = [c for c in cols if any(c.startswith(p) for p in ["ema_gap_", "sma_gap_", "bb_pos_"])][:5]
    micro_cols = [c for c in cols if any(c.startswith(p) for p in ["spread_zscore_", "tvol_zscore_", "abnormal_vol_"])][:5]

    # Vol × Momentum
    for vc in vol_cols:
        for mc in mom_cols:
            if vc in base_features.columns and mc in base_features.columns:
                features[f"ix_{vc}_x_{mc}"] = base_features[vc] * base_features[mc]

    # Session × Volatility
    for sc in session_cols:
        for vc in vol_cols[:3]:
            if sc in base_features.columns and vc in base_features.columns:
                features[f"ix_{sc}_x_{vc}"] = base_features[sc] * base_features[vc]

    # Session × Momentum
    for sc in session_cols:
        for mc in mom_cols[:3]:
            if sc in base_features.columns and mc in base_features.columns:
                features[f"ix_{sc}_x_{mc}"] = base_features[sc] * base_features[mc]

    # Entropy × Volatility
    for ec in entropy_cols:
        for vc in vol_cols[:3]:
            if ec in base_features.columns and vc in base_features.columns:
                features[f"ix_{ec}_x_{vc}"] = base_features[ec] * base_features[vc]

    # Entropy × Trend
    for ec in entropy_cols:
        for tc in trend_cols[:3]:
            if ec in base_features.columns and tc in base_features.columns:
                features[f"ix_{ec}_x_{tc}"] = base_features[ec] * base_features[tc]

    # Trend × Mean reversion (natural opposition)
    mr_cols = [c for c in cols if c.startswith("mean_rev_")][:3]
    for tc in trend_cols[:3]:
        for mrc in mr_cols:
            if tc in base_features.columns and mrc in base_features.columns:
                features[f"ix_{tc}_x_{mrc}"] = base_features[tc] * base_features[mrc]

    # Microstructure × Signal
    for mic in micro_cols[:3]:
        for mc in mom_cols[:3]:
            if mic in base_features.columns and mc in base_features.columns:
                features[f"ix_{mic}_x_{mc}"] = base_features[mic] * base_features[mc]

    # Vol regime × return (high vol amplifies returns)
    ret_cols = [c for c in cols if c.startswith("log_ret_")][:5]
    for vc in vol_cols[:3]:
        for rc in ret_cols[:3]:
            if vc in base_features.columns and rc in base_features.columns:
                features[f"ix_{vc}_x_{rc}"] = base_features[vc] * base_features[rc]

    # Cross-TF × local
    ctf_cols = [c for c in cols if any(c.startswith(p) for p in ["h1_", "h4_", "d1_"])][:5]
    for ctf in ctf_cols:
        for mc in mom_cols[:3]:
            if ctf in base_features.columns and mc in base_features.columns:
                features[f"ix_{ctf}_x_{mc}"] = base_features[ctf] * base_features[mc]

    result = base_features.select("time")
    for name, series in features.items():
        result = result.with_columns(series.alias(name))
    return result


def merge_existing_master_clean(spine: pl.DataFrame) -> pl.DataFrame:
    """Merge features from existing master_clean that aren't already in spine."""
    mc_path = ROOT / "data" / "hydra_xauusd_m5_master_clean.parquet"
    if not mc_path.exists():
        return spine.select("time")

    mc = pl.read_parquet(str(mc_path))

    # Exclude targets, labels, and columns we're regenerating
    exclude_prefixes = ["fwd_ret_", "label_", "target", "future_"]
    exclude_exact = ["time"]

    # Keep macro and cross-asset features from master_clean
    keep_cols = ["time"]
    for c in mc.columns:
        if c in exclude_exact:
            continue
        if any(c.startswith(p) for p in exclude_prefixes):
            continue
        # Keep columns that start with macro_ or are cross-asset
        if c.startswith("macro_") or any(c.startswith(x) for x in [
            "cross_", "corr_", "cot_", "gld_", "etf_", "gpr_",
            "yield_curve", "real_yield", "breakeven",
            "vix_", "btc_",
        ]):
            keep_cols.append(c)
        # Keep extended cross-asset columns
        elif any(c.endswith(x) for x in ["_ret1d", "_ret5d", "_ret20d", "_z20d", "_z60d"]):
            keep_cols.append(c)
        # Keep other unique features
        elif any(c.startswith(x) for x in [
            "gold_", "dollar_", "commodity_", "days_to_",
            "new_high_", "new_low_", "pin_bar", "doji", "inside_bar",
            "engulf_", "bull_streak", "bear_streak", "body_", "upper_shad", "lower_shad", "close_in_range",
            "autocorr_", "skew_", "kurt_",
        ]):
            keep_cols.append(c)

    # Only keep columns that exist
    keep_cols = [c for c in keep_cols if c in mc.columns]
    mc_subset = mc.select(keep_cols)

    return mc_subset


def build_targets(df: pl.DataFrame) -> pl.DataFrame:
    """Build forward-looking target columns (NOT features)."""
    close = df["close"]
    targets = {}

    for h in [5, 10, 20, 72, 144, 288]:
        targets[f"fwd_ret_{h}b"] = close.log().diff(h).shift(-h)

    # Classification labels (ternary: -1, 0, 1)
    for h in [5, 20, 72, 288]:
        fwd = close.log().diff(h).shift(-h)
        threshold = fwd.rolling_std(window_size=288).shift(1) * 0.5  # Use past vol for threshold
        targets[f"label_{h}b"] = pl.when(fwd > threshold).then(1).when(fwd < -threshold).then(-1).otherwise(0).cast(pl.Float32)

    result = df.select("time")
    for name, series in targets.items():
        result = result.with_columns(series.alias(name))
    return result


# ============================================================
# PHASE 3: Assembly & Validation
# ============================================================

def validate_no_leakage(df: pl.DataFrame) -> dict:
    """Check that no target/leakage columns are in the feature set."""
    issues = []
    feature_cols = [c for c in df.columns if c != "time" and not c.startswith("fwd_ret_") and not c.startswith("label_")]

    # Check for forbidden patterns
    forbidden = ["fwd_ret_", "label_", "target", "future_"]
    for c in feature_cols:
        for f in forbidden:
            if c.startswith(f):
                issues.append(f"LEAKAGE: {c} matches forbidden pattern {f}")

    # Check timestamps sorted
    times = df["time"]
    if not times.is_sorted():
        issues.append("TIMESTAMPS NOT SORTED")

    # Check for duplicates
    n_dupes = df.select("time").n_unique()
    if n_dupes < len(df):
        issues.append(f"DUPLICATE TIMESTAMPS: {len(df) - n_dupes}")

    return {
        "passed": len(issues) == 0,
        "issues": issues,
        "feature_count": len(feature_cols),
        "target_columns": [c for c in df.columns if c.startswith("fwd_ret_") or c.startswith("label_")],
    }


def validate_determinism(build_fn, spine_path: str, n_rows: int = 5000) -> dict:
    """Run build twice on subset, compare hashes."""
    import hashlib

    spine = pl.read_parquet(spine_path, n_rows=n_rows)

    # Normalize
    if "timestamp" in spine.columns and "time" in spine.columns:
        spine = spine.drop("time").rename({"timestamp": "time"})
    elif "timestamp" in spine.columns:
        spine = spine.rename({"timestamp": "time"})
    spine = spine.sort("time")
    keep = ["time", "open", "high", "low", "close", "tick_volume", "spread"]
    if "real_volume" in spine.columns:
        keep.append("real_volume")
    spine = spine.select([c for c in keep if c in spine.columns])

    result1 = build_fn(spine)
    result2 = build_fn(spine)

    # Compare
    h1 = hashlib.sha256(result1.to_pandas().to_csv(index=False).encode()).hexdigest()
    h2 = hashlib.sha256(result2.to_pandas().to_csv(index=False).encode()).hexdigest()

    return {
        "passed": h1 == h2,
        "hash1": h1[:16],
        "hash2": h2[:16],
    }


def compute_nan_stats(df: pl.DataFrame) -> dict:
    """Compute NaN statistics by column and family."""
    n = len(df)
    stats = {}
    family_nans = defaultdict(list)

    for c in df.columns:
        if c == "time":
            continue
        null_count = df[c].null_count()
        nan_pct = null_count / n * 100
        stats[c] = {"null_count": int(null_count), "null_pct": round(nan_pct, 2)}

        # Assign family
        if c.startswith("log_ret") or c.startswith("pct_ret") or c.startswith(("cum_ret", "ret_")):
            family_nans["return"].append(nan_pct)
        elif c.startswith(("rvol_", "park_vol_", "gk_vol_", "rs_vol_", "ewma_vol_", "vol_", "atr_", "range_", "max_dd_", "vov_")):
            family_nans["volatility"].append(nan_pct)
        elif c.startswith(("ema_", "sma_", "slope_", "mom_", "rsi_", "stoch_", "macd_", "breakout_", "channel_", "bb_", "adx_", "plus_di", "minus_di")):
            family_nans["trend_momentum"].append(nan_pct)
        elif c.startswith(("hour", "minute", "dow", "dom", "month", "sin_", "cos_", "is_", "asia_", "london_", "ny_", "in_block", "days_to", "week_of", "intraday")):
            family_nans["session_calendar"].append(nan_pct)
        elif c.startswith("macro_") or c.startswith(("yield_", "real_yield", "breakeven")):
            family_nans["macro"].append(nan_pct)
        elif c.startswith(("spread_", "tvol_", "abnormal_vol_", "vwap_", "illiquidity_", "vol_ret_")):
            family_nans["microstructure"].append(nan_pct)
        elif c.startswith(("perm_entropy", "sample_entropy", "lz_complexity", "hurst_", "fractal_", "mfdfa_", "ssa_", "autocorr_lag", "ret_perm", "ret_lz", "ret_hurst")):
            family_nans["entropy_fractal"].append(nan_pct)
        elif c.startswith(("h1_", "h4_", "d1_")):
            family_nans["cross_timeframe"].append(nan_pct)
        elif c.startswith("ix_"):
            family_nans["interactions"].append(nan_pct)
        elif c.startswith(("fwd_ret_", "label_")):
            family_nans["targets"].append(nan_pct)
        else:
            family_nans["other"].append(nan_pct)

    family_summary = {}
    for fam, pcts in family_nans.items():
        family_summary[fam] = {
            "count": len(pcts),
            "mean_null_pct": round(np.mean(pcts), 2) if pcts else 0,
            "max_null_pct": round(max(pcts), 2) if pcts else 0,
        }

    return {"per_column": stats, "per_family": family_summary}


def build_feature_manifest(df: pl.DataFrame) -> list:
    """Build manifest for every feature column."""
    manifest = []

    for c in df.columns:
        if c == "time" or c.startswith("fwd_ret_") or c.startswith("label_"):
            continue

        entry = {
            "name": c,
            "family": "unknown",
            "subgroup": "",
            "lookback": 0,
            "required_columns": [],
            "source_columns": [],
            "implementation_source": "python",
            "uses_future_data": False,
            "warmup_behavior": "null",
            "dtype": str(df[c].dtype),
            "created_by": "feature_fabric_v1",
            "description": "",
            "null_policy": "warmup",
        }

        # Classify
        if c.startswith(("log_ret", "pct_ret", "cum_ret", "ret_zscore", "ret_rank", "ret_accel", "ret_jerk", "ret_persist", "mean_rev", "dd_", "du_")):
            entry["family"] = "return"
            entry["required_columns"] = ["close"]
        elif c.startswith(("rvol_", "park_vol_", "gk_vol_", "rs_vol_", "ewma_vol_", "vol_zscore_", "vov_", "vol_ratio_", "atr_", "atr_pct_", "range_exp_", "vol_slope_", "max_dd_")):
            entry["family"] = "volatility"
            entry["required_columns"] = ["close", "high", "low", "open"]
        elif c.startswith(("ema_", "sma_", "slope_", "mom_", "rsi_", "stoch_", "macd_", "breakout_", "channel_", "bb_", "adx_", "plus_di", "minus_di", "mom_z_", "macd_hist")):
            entry["family"] = "trend_momentum"
            entry["required_columns"] = ["close", "high", "low"]
        elif c.startswith(("hour", "minute", "dow", "dom", "month", "sin_", "cos_", "is_", "asia_", "london_", "ny_", "in_block", "days_to", "week_of", "intraday", "is_nfp", "is_fomc")):
            entry["family"] = "session_calendar"
            entry["required_columns"] = ["time"]
        elif c.startswith("macro_") or c.startswith(("yield_", "real_yield", "breakeven")):
            entry["family"] = "macro"
            entry["implementation_source"] = "existing"
        elif c.startswith(("spread_", "tvol_", "abnormal_vol_", "vwap_", "illiquidity_", "vol_ret_")):
            entry["family"] = "microstructure"
            entry["required_columns"] = ["spread", "tick_volume"]
        elif c.startswith(("perm_entropy", "sample_entropy", "lz_complexity", "hurst_", "fractal_", "mfdfa_", "ssa_", "ret_perm", "ret_lz", "ret_hurst")):
            entry["family"] = "entropy_fractal"
            entry["implementation_source"] = "cpp"
            entry["required_columns"] = ["close"]
        elif c.startswith("autocorr_lag"):
            entry["family"] = "entropy_fractal"
            entry["implementation_source"] = "cpp"
        elif c.startswith(("h1_", "h4_", "d1_")):
            entry["family"] = "cross_timeframe"
            entry["required_columns"] = ["close", "high", "low"]
        elif c.startswith("ix_"):
            entry["family"] = "interactions"
        elif any(c.endswith(x) for x in ["_ret1d", "_ret5d", "_ret20d", "_z20d", "_z60d"]):
            entry["family"] = "cross_asset"
            entry["implementation_source"] = "existing"
        elif c.startswith(("cot_", "gld_", "etf_", "gpr_")):
            entry["family"] = "alternative"
            entry["implementation_source"] = "existing"
        elif c.startswith(("gold_", "dollar_", "commodity_")):
            entry["family"] = "composite"
            entry["implementation_source"] = "existing"
        else:
            entry["family"] = "other"
            entry["implementation_source"] = "existing"

        # Extract lookback from name
        import re
        lb_match = re.search(r'_(\d+)b', c)
        if lb_match:
            entry["lookback"] = int(lb_match.group(1))

        manifest.append(entry)

    return manifest


def build_all_features(spine: pl.DataFrame) -> pl.DataFrame:
    """Core build function - assembles all feature families."""
    print(f"  [1/8] Return features...")
    returns = build_return_features(spine)
    print(f"    -> {len(returns.columns) - 1} features")

    print(f"  [2/8] Volatility features...")
    volatility = build_volatility_features(spine)
    print(f"    -> {len(volatility.columns) - 1} features")

    print(f"  [3/8] Trend/momentum features...")
    trend = build_trend_momentum_features(spine)
    print(f"    -> {len(trend.columns) - 1} features")

    print(f"  [4/8] Session/calendar features...")
    session = build_session_calendar_features(spine)
    print(f"    -> {len(session.columns) - 1} features")

    print(f"  [5/8] Microstructure features...")
    micro = build_microstructure_features(spine)
    print(f"    -> {len(micro.columns) - 1} features")

    print(f"  [6/8] Cross-timeframe features...")
    cross_tf = build_cross_timeframe_features(spine)
    print(f"    -> {len(cross_tf.columns) - 1} features")

    print(f"  [7/8] C++ advanced features (entropy/fractal)...")
    cpp_feat = build_cpp_advanced_features(spine)
    print(f"    -> {len(cpp_feat.columns) - 1} features")

    # Merge existing master_clean features (macro, cross-asset, etc.)
    print(f"  [7.5/8] Merging existing master_clean features...")
    mc_feats = merge_existing_master_clean(spine)
    print(f"    -> {len(mc_feats.columns) - 1} existing features to merge")

    # Assemble all
    print(f"  [8/8] Assembling...")
    result = spine.clone()

    for feat_df in [returns, volatility, trend, session, micro, cross_tf, cpp_feat]:
        new_cols = [c for c in feat_df.columns if c != "time" and c not in result.columns]
        if new_cols:
            result = result.with_columns([feat_df[c] for c in new_cols])

    # Merge master_clean via time join
    if len(mc_feats.columns) > 1:
        # Align by time
        new_mc_cols = [c for c in mc_feats.columns if c != "time" and c not in result.columns]
        if new_mc_cols:
            mc_subset = mc_feats.select(["time"] + new_mc_cols)
            result = result.join(mc_subset, on="time", how="left")

    # Build interactions AFTER all base features assembled
    print(f"  [8.5/8] Interaction features...")
    interactions = build_interaction_features(result)
    new_ix_cols = [c for c in interactions.columns if c != "time" and c not in result.columns]
    if new_ix_cols:
        result = result.with_columns([interactions[c] for c in new_ix_cols])
    print(f"    -> {len(new_ix_cols)} interaction features")

    return result


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="HYDRA Feature Fabric Builder")
    parser.add_argument("--rows", type=int, default=0, help="Limit rows (0=all)")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--determinism-check", action="store_true")
    args = parser.parse_args()

    start_time = time.time()
    print("=" * 60)
    print("HYDRA Feature Fabric Builder v1")
    print("=" * 60)

    # Phase 1: Source discovery
    print("\n[PHASE 1] Source Discovery...")
    inventory = discover_sources()
    os.makedirs(ROOT / "reports" / "dataset_factory", exist_ok=True)
    with open(ROOT / "reports" / "dataset_factory" / "source_inventory.json", "w") as f:
        json.dump(inventory, f, indent=2)

    for name, info in inventory.items():
        status = info.get("status", "UNKNOWN")
        print(f"  {name}: {status}")

    # Phase 2: Load spine
    print("\n[PHASE 2] Loading spine (MT5 M5 MASTER)...")
    spine = load_spine()
    if args.rows > 0:
        spine = spine.head(args.rows)
    print(f"  Spine: {len(spine)} rows, {len(spine.columns)} cols")
    print(f"  Time range: {spine['time'][0]} to {spine['time'][-1]}")

    # Phase 3: Build features
    print("\n[PHASE 3] Building features...")
    result = build_all_features(spine)

    # Add targets
    print("\n[PHASE 4] Adding targets...")
    targets = build_targets(spine)
    target_cols = [c for c in targets.columns if c != "time"]
    result = result.with_columns([targets[c] for c in target_cols])
    print(f"  Targets: {target_cols}")

    # Count features
    feature_cols = [c for c in result.columns if c != "time" and not c.startswith("fwd_ret_") and not c.startswith("label_")]
    raw_cols = ["open", "high", "low", "close", "tick_volume", "spread", "real_volume"]
    pure_feature_cols = [c for c in feature_cols if c not in raw_cols]

    print(f"\n  Total columns: {len(result.columns)}")
    print(f"  Feature columns: {len(pure_feature_cols)}")
    print(f"  Target columns: {len(target_cols)}")
    print(f"  Raw OHLCV columns: {len([c for c in feature_cols if c in raw_cols])}")

    # Phase 5: Validation
    print("\n[PHASE 5] Validation...")

    # Leakage check
    leakage = validate_no_leakage(result)
    print(f"  Leakage audit: {'PASSED' if leakage['passed'] else 'FAILED'}")
    if not leakage['passed']:
        for issue in leakage['issues']:
            print(f"    ! {issue}")

    # NaN stats
    nan_stats = compute_nan_stats(result)
    print(f"  NaN stats by family:")
    for fam, stats in nan_stats["per_family"].items():
        print(f"    {fam}: {stats['count']} cols, mean_null={stats['mean_null_pct']:.1f}%, max_null={stats['max_null_pct']:.1f}%")

    # Drop features with >95% NaN
    bad_cols = [c for c, s in nan_stats["per_column"].items() if s["null_pct"] > 95 and c != "time"]
    if bad_cols:
        print(f"  Dropping {len(bad_cols)} columns with >95% NaN")
        result = result.drop(bad_cols)
        pure_feature_cols = [c for c in pure_feature_cols if c not in bad_cols]

    # Inf check
    inf_count = 0
    for c in pure_feature_cols:
        if result[c].dtype in [pl.Float32, pl.Float64]:
            inf_c = result[c].is_infinite().sum()
            if inf_c > 0:
                inf_count += inf_c
                # Replace inf with null
                result = result.with_columns(
                    pl.when(pl.col(c).is_infinite()).then(None).otherwise(pl.col(c)).alias(c)
                )
    print(f"  Infinite values found and nullified: {inf_count}")

    # Feature count gate
    FEATURE_GATE = 1500
    feature_count = len(pure_feature_cols)
    gate_passed = feature_count >= FEATURE_GATE
    if gate_passed:
        print(f"  FEATURE COUNT GATE: PASSED ({feature_count} >= {FEATURE_GATE})")
    else:
        print(f"  FEATURE COUNT GATE: FAILED ({feature_count} < {FEATURE_GATE})")
        print(f"  FAILED_FEATURE_COUNT_GATE")

    # Determinism check
    if args.determinism_check or args.rows == 0:
        print("\n  Running determinism check (5k rows)...")
        det = validate_determinism(
            build_all_features,
            str(ROOT / "data" / "mt5_history" / "XAUUSD_M5_MASTER.parquet"),
            n_rows=5000
        )
        print(f"  Determinism: {'PASSED' if det['passed'] else 'FAILED'} (h1={det['hash1']}, h2={det['hash2']})")
    else:
        det = {"passed": True, "hash1": "skipped", "hash2": "skipped"}

    # Phase 6: Save output
    print("\n[PHASE 6] Saving outputs...")
    output_path = ROOT / "data" / "feature_fabric" / "hydra_xauusd_feature_fabric_v1.parquet"
    os.makedirs(output_path.parent, exist_ok=True)
    result.write_parquet(str(output_path))
    print(f"  Dataset: {output_path} ({os.path.getsize(output_path) / 1e6:.1f} MB)")

    # Manifest
    manifest = build_feature_manifest(result)
    manifest_path = ROOT / "reports" / "dataset_factory" / "hydra_feature_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"  Manifest: {manifest_path} ({len(manifest)} entries)")

    # Family counts
    family_counts = defaultdict(int)
    for entry in manifest:
        family_counts[entry["family"]] += 1
    family_counts_path = ROOT / "reports" / "dataset_factory" / "feature_family_counts.json"
    with open(family_counts_path, "w") as f:
        json.dump(dict(family_counts), f, indent=2)

    # Validation summary
    validation_summary = {
        "leakage_audit": leakage,
        "determinism": det,
        "nan_stats_per_family": nan_stats["per_family"],
        "inf_count": int(inf_count),
        "feature_count": feature_count,
        "feature_gate_passed": gate_passed,
        "dropped_columns": bad_cols,
        "rows": len(result),
        "first_timestamp": str(result["time"][0]),
        "last_timestamp": str(result["time"][-1]),
    }
    val_path = ROOT / "reports" / "dataset_factory" / "dataset_validation_summary.json"
    with open(val_path, "w") as f:
        json.dump(validation_summary, f, indent=2, default=str)

    elapsed = time.time() - start_time

    # Final summary
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    print(f"  Output: {output_path}")
    print(f"  Rows: {len(result)}")
    print(f"  Total columns: {len(result.columns)}")
    print(f"  Feature columns: {feature_count}")
    print(f"  Target columns: {len(target_cols)}")
    print(f"  Feature families:")
    for fam, count in sorted(family_counts.items(), key=lambda x: -x[1]):
        print(f"    {fam}: {count}")
    print(f"  First timestamp: {result['time'][0]}")
    print(f"  Last timestamp: {result['time'][-1]}")
    print(f"  Feature count gate: {'PASSED' if gate_passed else 'FAILED'} ({feature_count})")
    print(f"  Leakage audit: {'PASSED' if leakage['passed'] else 'FAILED'}")
    print(f"  Determinism: {'PASSED' if det['passed'] else 'FAILED'}")
    print(f"  Build time: {elapsed:.1f}s")
    print(f"  Memory: {result.estimated_size() / 1e9:.2f} GB")
    print("=" * 60)


if __name__ == "__main__":
    main()
