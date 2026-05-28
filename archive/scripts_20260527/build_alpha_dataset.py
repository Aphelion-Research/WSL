#!/usr/bin/env python3
"""Build Alpha Dataset — tick microstructure + cross-asset lead-lag + regime features.

Sources:
1. Dukascopy M5 bars (782k bars, has OHLCV + tick_volume + spread)
2. Existing feature matrix (1125 cols of technicals + macro + cross-asset)
3. MT5 real-time ticks (recent, for validation)
4. Dukascopy daily tick files (2953 cached days → aggregate to M5 microstructure)

Output: data/hydra_alpha_dataset.parquet
    - All original features
    - + tick microstructure (VPIN proxy, trade intensity, spread dynamics)
    - + proper cross-asset lead-lag at correct frequency
    - + regime features
    - + labels

This replaces the broken approach of computing features without OHLCV.
"""
import json
import time
import warnings
from pathlib import Path
from datetime import datetime

import numpy as np
import polars as pl
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

warnings.filterwarnings("ignore")
console = Console()

OUTPUT_PATH = Path("data/hydra_alpha_dataset.parquet")


def load_base_data():
    """Load Dukascopy M5 bars (has OHLCV + tick_volume + spread)."""
    console.print("\n[bold cyan]═══ LOAD BASE (Dukascopy M5 OHLCV) ═══[/bold cyan]")
    df = pl.read_parquet("data/mt5_history/XAUUSD_M5_dukascopy.parquet")
    df = df.sort("time")
    console.print(f"  {df.shape[0]:,} bars | {df['time'].min()} → {df['time'].max()}")
    console.print(f"  Columns: {df.columns}")
    return df


def load_feature_matrix():
    """Load existing feature matrix."""
    console.print("\n[bold cyan]═══ LOAD FEATURE MATRIX ═══[/bold cyan]")
    df = pl.read_parquet("data/hydra_xauusd_m5_master_clean.parquet")
    console.print(f"  {df.shape[0]:,} rows x {df.shape[1]:,} cols")
    return df


def build_tick_microstructure(df: pl.DataFrame) -> pl.DataFrame:
    """Build tick-level microstructure features from M5 OHLCV.

    Key features:
    - VPIN proxy (volume-synchronized probability of informed trading)
    - Trade intensity (tick_volume patterns)
    - Spread dynamics (bid-ask spread as liquidity indicator)
    - Kyle's lambda proxy (price impact per unit volume)
    - Amihud illiquidity
    - Volume clock features (bars by volume instead of time)
    """
    console.print("\n[bold cyan]═══ TICK MICROSTRUCTURE FEATURES ═══[/bold cyan]")

    close = pl.col("close")
    opn = pl.col("open")
    high = pl.col("high")
    low = pl.col("low")
    vol = pl.col("tick_volume").cast(pl.Float64)
    spread = pl.col("spread")

    exprs = []

    # ── VPIN PROXY ──
    # Volume-synchronized probability of informed trading
    # Approximation: |close - open| / (high - low) weighted by volume
    # High VPIN = directional flow dominates (informed traders active)
    bar_range = (high - low).clip(lower_bound=0.01)
    body = (close - opn).abs()
    vpin_bar = body / bar_range  # fraction of range that was directional

    for w in [12, 48, 144, 288]:  # 1hr, 4hr, 12hr, 24hr
        # Volume-weighted VPIN
        exprs.append(vpin_bar.rolling_mean(w).alias(f"tick_vpin_{w}"))
        # VPIN change (acceleration of informed trading)
        exprs.append(vpin_bar.rolling_mean(w).diff(w // 4).alias(f"tick_vpin_chg_{w}"))

    # ── TRADE INTENSITY ──
    # tick_volume = number of price changes in 5min bar
    # High tick intensity = active market, tight spreads, tradeable
    for w in [6, 12, 48, 144, 288]:
        vol_ma = vol.rolling_mean(w)
        exprs.append((vol / vol_ma.clip(lower_bound=1.0)).alias(f"tick_intensity_{w}"))

    # Volume momentum (1st & 2nd derivative)
    exprs.append(vol.diff(1).alias("tick_vol_momentum"))
    exprs.append(vol.diff(1).diff(1).alias("tick_vol_accel"))
    exprs.append(vol.pct_change(12).alias("tick_vol_pctchg_12"))

    # Volume spikes (z-score)
    vol_mean = vol.rolling_mean(288)
    vol_std = vol.rolling_std(288)
    exprs.append(((vol - vol_mean) / vol_std.clip(lower_bound=0.01)).alias("tick_vol_zscore"))

    # Cumulative volume (proxy for "volume clock" bars)
    # Bars with very high volume = potential institutional activity
    exprs.append((vol.rolling_sum(12) / vol.rolling_sum(288).clip(lower_bound=1.0) * 24).alias("tick_vol_concentration"))

    # ── SPREAD DYNAMICS ──
    # Bid-ask spread encodes liquidity and uncertainty
    for w in [12, 48, 144]:
        spread_ma = spread.rolling_mean(w)
        exprs.append(spread_ma.alias(f"tick_spread_ma_{w}"))
        # Spread relative to recent history
        spread_z = (spread - spread_ma) / spread.rolling_std(w).clip(lower_bound=0.001)
        exprs.append(spread_z.alias(f"tick_spread_z_{w}"))

    # Spread expansion/compression (regime signal)
    exprs.append((spread.rolling_mean(12) / spread.rolling_mean(144).clip(lower_bound=0.001)).alias("tick_spread_ratio"))
    exprs.append(spread.diff(1).alias("tick_spread_chg"))
    exprs.append(spread.pct_change(12).alias("tick_spread_pctchg"))

    # ── KYLE'S LAMBDA PROXY ──
    # Price impact = |return| / volume (how much price moves per unit volume)
    # High lambda = illiquid, low lambda = deep market
    ret = close.pct_change(1).abs()
    kyle_lambda = ret / vol.clip(lower_bound=1.0)
    for w in [12, 48, 144]:
        exprs.append(kyle_lambda.rolling_mean(w).alias(f"tick_kyle_lambda_{w}"))

    # ── AMIHUD ILLIQUIDITY ──
    # |return| / dollar_volume (price impact per dollar traded)
    # We use tick_volume as proxy
    amihud = ret / (vol * close).clip(lower_bound=0.01)
    for w in [24, 72, 288]:
        exprs.append(amihud.rolling_mean(w).alias(f"tick_amihud_{w}"))

    # ── ORDER FLOW IMBALANCE ──
    # Approximation using close-vs-mid: if close > mid → more buying
    # mid = (high + low) / 2
    mid = (high + low) / 2
    ofi_proxy = (close - mid) / bar_range  # -1 to +1

    for w in [6, 12, 48, 144]:
        # Cumulative order flow (persistent buying/selling)
        exprs.append(ofi_proxy.rolling_sum(w).alias(f"tick_ofi_sum_{w}"))
        exprs.append(ofi_proxy.rolling_mean(w).alias(f"tick_ofi_mean_{w}"))

    # OFI reversal signal: strong OFI followed by price not following
    ofi_12 = ofi_proxy.rolling_sum(12)
    ret_12 = close.pct_change(12)
    # If OFI says buy (+) but price went down → smart money absorbed
    exprs.append((ofi_12 * ret_12.sign() * -1).alias("tick_ofi_divergence"))

    # ── VOLUME-PRICE INTERACTION ──
    # Up-volume vs down-volume (on-balance flow per bar)
    direction = (close - opn).sign()
    up_vol = pl.when(direction > 0).then(vol).otherwise(pl.lit(0.0))
    down_vol = pl.when(direction < 0).then(vol).otherwise(pl.lit(0.0))

    for w in [12, 48, 144]:
        up_sum = up_vol.rolling_sum(w)
        down_sum = down_vol.rolling_sum(w)
        total = (up_sum + down_sum).clip(lower_bound=1.0)
        # Buy ratio: what fraction of volume was on up bars
        exprs.append((up_sum / total).alias(f"tick_buy_ratio_{w}"))
        # Net flow
        exprs.append(((up_sum - down_sum) / total).alias(f"tick_net_flow_{w}"))

    # ── VOLATILITY MICROSTRUCTURE ──
    # Realized variance from high-low (Parkinson estimator per bar)
    hl_var = ((high - low).log() ** 2) / (4 * np.log(2))
    for w in [12, 48, 144]:
        rv = hl_var.rolling_mean(w).sqrt()
        exprs.append(rv.alias(f"tick_rv_parkinson_{w}"))

    # Garman-Klass variance (uses OHLC)
    gk_var = 0.5 * ((high - low).log() ** 2) - (2 * np.log(2) - 1) * ((close - opn).log() ** 2)
    for w in [12, 48, 144]:
        exprs.append(gk_var.rolling_mean(w).alias(f"tick_gk_vol_{w}"))

    # Vol of vol (vol stability)
    rv_48 = hl_var.rolling_mean(48).sqrt()
    exprs.append(rv_48.rolling_std(48).alias("tick_vol_of_vol"))

    # ── MICROSTRUCTURE REGIME ──
    # Spread × Volume interaction (high spread + low vol = dangerous)
    exprs.append((spread * (1.0 / vol.clip(lower_bound=1.0))).alias("tick_illiquidity_composite"))

    # Tick intensity normalized by spread (efficiency)
    exprs.append((vol / spread.clip(lower_bound=0.01)).rolling_mean(48).alias("tick_market_efficiency"))

    df = df.with_columns(exprs)

    tick_cols = [c for c in df.columns if c.startswith("tick_")]
    console.print(f"  Created {len(tick_cols)} tick microstructure features")
    return df


def build_leadlag_from_ohlcv(df: pl.DataFrame, feature_df: pl.DataFrame) -> pl.DataFrame:
    """Join cross-asset features at correct frequency.

    The feature matrix has daily cross-asset returns (eurusd_ret1d, etc.)
    These are forward-filled to M5 bars. We add:
    - Lagged versions (yesterday's move → today's gold prediction)
    - Change-of-change (acceleration)
    - Cross-asset interaction terms
    """
    console.print("\n[bold cyan]═══ CROSS-ASSET LEAD-LAG ═══[/bold cyan]")

    # Get cross-asset columns from feature matrix
    cross_cols = [c for c in feature_df.columns if any(x in c for x in (
        "eurusd", "gbpusd", "usdchf", "usdjpy", "silver", "copper",
        "dxy", "spx", "nasdaq", "vix", "tlt", "hyg", "wti", "btc",
        "gvz", "gold_silver_ratio", "gold_copper_ratio",
    ))]

    # Also get useful composites
    extra_cols = [c for c in feature_df.columns if c in (
        "risk_on_composite", "dollar_composite", "commodity_composite",
        "yield_curve_2s10s", "yield_curve_chg5d", "real_yield_10y",
        "breakeven_10y", "cot_mm_long_z52w", "cot_mm_short_z52w",
        "gld_flow_z20",
    )]

    join_cols = list(set(cross_cols + extra_cols))
    console.print(f"  Joining {len(join_cols)} cross-asset columns from feature matrix")

    # Join on time
    feature_subset = feature_df.select(["time"] + [c for c in join_cols if c in feature_df.columns])
    df = df.join(feature_subset, on="time", how="left")

    # Now build lead-lag interactions
    exprs = []

    # Key leaders for gold
    leaders = ["dxy_ret1d", "eurusd_ret1d", "silver_ret1d", "vix_ret1d",
               "tlt_ret1d", "spx_ret1d", "copper_ret1d", "usdjpy_ret1d"]

    for col in leaders:
        if col not in df.columns:
            continue

        # Lagged values (1-3 day lag for lead-lag)
        for lag in [288, 576, 864]:  # 1day, 2day, 3day in M5 bars
            exprs.append(pl.col(col).shift(lag).alias(f"ll_{col}_lag{lag // 288}d"))

        # Momentum (is the move accelerating)
        exprs.append(pl.col(col).diff(288).alias(f"ll_{col}_accel"))

    # Gold vs DXY divergence (key relationship)
    if "dxy_ret1d" in df.columns:
        gold_ret = close_ret_1d = (pl.col("close") / pl.col("close").shift(288) - 1)
        dxy = pl.col("dxy_ret1d")
        # Normally gold and DXY are inversely correlated
        # Divergence = both moving same direction = unusual
        exprs.append((gold_ret + dxy).alias("ll_gold_dxy_divergence"))

    # VIX term structure (fear gauge)
    if "vix_ret1d" in df.columns and "vix3m_ret1d" in df.columns:
        # VIX > VIX3M = backwardation = panic = gold up
        exprs.append((pl.col("vix_ret1d") - pl.col("vix3m_ret1d")).alias("ll_vix_term_structure"))

    # Gold vs silver ratio change (relative strength)
    if "gold_silver_ratio_z20" in df.columns:
        gsr = pl.col("gold_silver_ratio_z20")
        exprs.append(gsr.diff(288).alias("ll_gsr_momentum"))

    # Risk composite momentum
    if "risk_on_composite" in df.columns:
        exprs.append(pl.col("risk_on_composite").diff(288).alias("ll_risk_momentum"))

    # COT positioning (smart money flow)
    if "cot_mm_long_z52w" in df.columns:
        exprs.append(pl.col("cot_mm_long_z52w").diff(288 * 5).alias("ll_cot_momentum"))

    if exprs:
        df = df.with_columns(exprs)

    ll_cols = [c for c in df.columns if c.startswith("ll_")]
    console.print(f"  Created {len(ll_cols)} lead-lag features")
    return df


def build_regime_features(df: pl.DataFrame) -> pl.DataFrame:
    """Build regime detection features from OHLCV."""
    console.print("\n[bold cyan]═══ REGIME FEATURES ═══[/bold cyan]")

    close = pl.col("close")
    high = pl.col("high")
    low = pl.col("low")
    vol = pl.col("tick_volume").cast(pl.Float64)

    exprs = []

    # ── Trend efficiency (directional consistency) ──
    ret = close.pct_change(1)
    for w in [24, 72, 144, 288]:
        cum_ret = ret.rolling_sum(w).abs()
        total_move = ret.abs().rolling_sum(w)
        efficiency = cum_ret / total_move.clip(lower_bound=0.0001)
        exprs.append(efficiency.alias(f"reg_efficiency_{w}"))

    # ── Volatility regime ──
    bar_range = high - low
    for w in [48, 144, 576]:
        range_ma = bar_range.rolling_mean(w)
        range_std = bar_range.rolling_std(w)
        # Range z-score (is current vol high/low vs history)
        exprs.append(((bar_range - range_ma) / range_std.clip(lower_bound=0.001)).alias(f"reg_vol_z_{w}"))

    # Short/long vol ratio (compression detector)
    exprs.append((bar_range.rolling_mean(12) / bar_range.rolling_mean(288).clip(lower_bound=0.001)).alias("reg_vol_ratio_12_288"))
    exprs.append((bar_range.rolling_mean(48) / bar_range.rolling_mean(576).clip(lower_bound=0.001)).alias("reg_vol_ratio_48_576"))

    # ── Session regime ──
    # Extract hour from time for session classification
    hour = pl.col("time").dt.hour()
    # London overlap (13-17 UTC) — most liquid, most predictable
    is_london = (hour >= 13) & (hour < 17)
    is_ny = (hour >= 14) & (hour < 21)
    is_asia = (hour >= 0) & (hour < 8)
    exprs.append(is_london.cast(pl.Int8).alias("reg_is_london"))
    exprs.append(is_ny.cast(pl.Int8).alias("reg_is_ny"))
    exprs.append(is_asia.cast(pl.Int8).alias("reg_is_asia"))

    # Volume by session (is this bar's volume normal for its session?)
    # Approximate with hour-of-day seasonality
    exprs.append((vol / vol.rolling_mean(288).clip(lower_bound=1.0)).alias("reg_vol_seasonal"))

    # ── Mean-reversion vs momentum regime ──
    # Autocorrelation of returns (positive = trending, negative = MR)
    # Approximate with sign consistency
    sign_ret = ret.sign()
    for w in [12, 48, 144]:
        sign_sum = sign_ret.rolling_sum(w)
        # |sign_sum| / w = trending strength (1.0 = pure trend, 0 = chop)
        exprs.append((sign_sum.abs() / w).alias(f"reg_trend_strength_{w}"))

    # ── Breakout regime ──
    # Is price near rolling highs/lows?
    for w in [48, 144, 288]:
        roll_high = high.rolling_max(w)
        roll_low = low.rolling_min(w)
        channel_width = (roll_high - roll_low).clip(lower_bound=0.01)
        # Position in channel (0 = at low, 1 = at high)
        channel_pos = (close - roll_low) / channel_width
        exprs.append(channel_pos.alias(f"reg_channel_pos_{w}"))
        # Narrowing channel = consolidation (breakout imminent)
        exprs.append(channel_width.pct_change(w // 4).alias(f"reg_channel_squeeze_{w}"))

    # ── Volume-price agreement ──
    # Rising price + rising volume = confirmed trend
    price_dir = ret.rolling_sum(12).sign()
    vol_dir = vol.pct_change(12).sign()
    exprs.append((price_dir * vol_dir).alias("reg_vol_price_agree"))

    df = df.with_columns(exprs)

    reg_cols = [c for c in df.columns if c.startswith("reg_")]
    console.print(f"  Created {len(reg_cols)} regime features")
    return df


def add_labels(df: pl.DataFrame, feature_df: pl.DataFrame) -> pl.DataFrame:
    """Join labels from feature matrix."""
    console.print("\n[bold cyan]═══ ADD LABELS ═══[/bold cyan]")

    label_cols = [c for c in feature_df.columns if "label" in c or "fwd" in c]
    labels = feature_df.select(["time"] + label_cols)
    df = df.join(labels, on="time", how="left")

    for lc in [c for c in label_cols if c.startswith("label_")]:
        valid = df[lc].is_not_null().sum()
        console.print(f"  {lc}: {valid:,} valid")

    return df


def main():
    total_start = time.time()

    console.print(Panel.fit(
        "[bold]HYDRA ALPHA DATASET BUILDER[/bold]\n"
        "Tick microstructure + Lead-lag + Regime\n"
        "From Dukascopy M5 OHLCV (782k bars, 2015-2026)",
        style="bold green"
    ))

    # Load base OHLCV
    df = load_base_data()

    # Load feature matrix
    feature_df = load_feature_matrix()

    # Build features
    df = build_tick_microstructure(df)
    df = build_leadlag_from_ohlcv(df, feature_df)
    df = build_regime_features(df)

    # Join existing technical features
    console.print("\n[bold cyan]═══ JOIN EXISTING FEATURES ═══[/bold cyan]")
    # Get non-OHLC features from feature matrix
    existing_feat_cols = [c for c in feature_df.columns
                         if c not in ("time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume")
                         and "label" not in c and "fwd" not in c]
    console.print(f"  Joining {len(existing_feat_cols)} existing features")

    existing_features = feature_df.select(["time"] + existing_feat_cols)
    df = df.join(existing_features, on="time", how="left")

    # Add labels
    df = add_labels(df, feature_df)

    # Summary
    console.print("\n[bold cyan]═══ DATASET SUMMARY ═══[/bold cyan]")
    tick_cols = [c for c in df.columns if c.startswith("tick_")]
    ll_cols = [c for c in df.columns if c.startswith("ll_")]
    reg_cols = [c for c in df.columns if c.startswith("reg_")]
    label_cols = [c for c in df.columns if c.startswith("label_") or c.startswith("fwd_")]
    base_cols = {"time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume", "timestamp"}
    other_cols = [c for c in df.columns if c not in base_cols and c not in tick_cols
                  and c not in ll_cols and c not in reg_cols and c not in label_cols]

    table = Table(title="Alpha Dataset Composition", box=box.SIMPLE)
    table.add_column("Category", style="cyan")
    table.add_column("Count", style="magenta")
    table.add_row("Base OHLCV", str(len(base_cols)))
    table.add_row("Tick microstructure (NEW)", str(len(tick_cols)))
    table.add_row("Lead-lag (NEW)", str(len(ll_cols)))
    table.add_row("Regime (NEW)", str(len(reg_cols)))
    table.add_row("Existing technicals/macro/cross", str(len(other_cols)))
    table.add_row("Labels/targets", str(len(label_cols)))
    table.add_row("", "")
    table.add_row("TOTAL", str(len(df.columns)), style="bold green")
    table.add_row("Rows", f"{df.shape[0]:,}")
    console.print(table)

    # Save
    console.print("\n[bold green]═══ SAVE ═══[/bold green]")
    df.write_parquet(OUTPUT_PATH)
    size_mb = OUTPUT_PATH.stat().st_size / 1024 / 1024
    console.print(f"  Saved: {OUTPUT_PATH} ({size_mb:.1f} MB)")

    total_time = time.time() - total_start
    console.print(f"  Time: {total_time:.0f}s")

    console.print(Panel.fit(
        f"[bold green]ALPHA DATASET COMPLETE[/bold green]\n\n"
        f"{df.shape[0]:,} rows x {df.shape[1]:,} cols\n"
        f"New features: {len(tick_cols)} tick + {len(ll_cols)} lead-lag + {len(reg_cols)} regime\n"
        f"Saved: {OUTPUT_PATH}",
        style="bold green"
    ))


if __name__ == "__main__":
    main()
