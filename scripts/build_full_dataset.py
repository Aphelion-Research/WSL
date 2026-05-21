#!/usr/bin/env python3
"""
Build complete HYDRA dataset with all available sources.
Uses real DuckDB data + MT5 history + C++ kernels.
"""
import sys
from pathlib import Path
import duckdb
import pandas as pd
import polars as pl
import numpy as np
from datetime import datetime, timezone

# Add repo to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dominion.features import cpp_bridge
from dominion.dataset.registries import HydraRegistry
from dominion.quality.gates import run_all_gates, print_gate_report

# Import M5 feature expansion
sys.path.insert(0, str(Path(__file__).parent))
from m5_feature_expansion import add_all_expanded_features


def load_gold_ohlcv(con: duckdb.DuckDBPyConnection, timeframe: str = "D1") -> pd.DataFrame:
    """Load gold OHLCV from DuckDB gold_master or MT5 history."""
    print(f"Loading gold OHLCV ({timeframe})...")

    if timeframe == "D1":
        # Use gold_master (daily)
        df = con.execute("""
            SELECT
                timestamp as time,
                open, high, low, close, volume
            FROM gold_master
            ORDER BY timestamp
        """).df()
    else:
        # Use MT5 history
        mt5_path = Path(f"data/mt5_history/XAUUSD_{timeframe}.parquet")
        if not mt5_path.exists():
            raise FileNotFoundError(f"MT5 data not found: {mt5_path}")

        df = pd.read_parquet(mt5_path)
        df['time'] = pd.to_datetime(df['time'], unit='s', utc=True)

        # Add volume if missing (MT5 tick_volume or synthetic)
        if 'volume' not in df.columns:
            if 'tick_volume' in df.columns:
                df['volume'] = df['tick_volume']
            else:
                df['volume'] = 1000  # Synthetic default

    print(f"  Loaded {len(df)} bars: {df['time'].min()} to {df['time'].max()}")
    return df


def load_macro(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Load macro data from DuckDB."""
    print("Loading macro data...")

    df = con.execute("""
        SELECT
            timestamp as time,
            value,
            series_id
        FROM macro_data
        ORDER BY timestamp, series_id
    """).df()

    # Pivot to wide format
    macro_wide = df.pivot(index='time', columns='series_id', values='value')
    macro_wide.columns = [f'macro_{c}' for c in macro_wide.columns]
    macro_wide = macro_wide.reset_index()

    print(f"  Loaded {len(macro_wide)} rows, {len(macro_wide.columns)-1} series")
    return macro_wide


def load_cot(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Load COT data from DuckDB."""
    print("Loading COT data...")

    df = con.execute("""
        SELECT
            report_date as time,
            commercial_long,
            commercial_short,
            noncommercial_long,
            noncommercial_short,
            open_interest
        FROM cot_data
        ORDER BY report_date
    """).df()

    df.columns = [f'cot_{c}' if c != 'time' else c for c in df.columns]

    print(f"  Loaded {len(df)} weekly reports")
    return df


def load_regime(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Load regime labels from DuckDB."""
    print("Loading regime labels...")

    df = con.execute("""
        SELECT
            timestamp as time,
            micro_regime as regime,
            confidence
        FROM regime_labels
        ORDER BY timestamp
    """).df()

    # One-hot encode regime
    regime_dummies = pd.get_dummies(df['regime'], prefix='regime')
    df = pd.concat([df[['time', 'confidence']], regime_dummies], axis=1)
    df.columns = [f'regime_{c}' if c not in ['time', 'confidence'] else c for c in df.columns]

    print(f"  Loaded {len(df)} regime labels")
    return df


def asof_join_safe(left: pd.DataFrame, right: pd.DataFrame, on: str = 'time') -> pd.DataFrame:
    """Point-in-time safe asof join (backward only)."""
    left = left.sort_values(on)
    right = right.sort_values(on)

    # Ensure matching datetime precision (force to nanoseconds)
    if pd.api.types.is_datetime64_any_dtype(left[on]):
        left = left.copy()
        left[on] = pd.to_datetime(left[on], utc=True).astype('datetime64[ns, UTC]')
    if pd.api.types.is_datetime64_any_dtype(right[on]):
        right = right.copy()
        right[on] = pd.to_datetime(right[on], utc=True).astype('datetime64[ns, UTC]')

    result = pd.merge_asof(
        left,
        right,
        on=on,
        direction='backward',
        allow_exact_matches=True
    )

    return result


def compute_rolling_features(df: pd.DataFrame, col: str, windows: list[int]) -> pd.DataFrame:
    """Compute rolling features using C++ kernels."""
    print(f"Computing rolling features for {col}...")

    features = {}

    # Convert pandas to polars for C++ bridge
    df_pl = pl.from_pandas(df)

    for w in windows:
        features[f'{col}_mean_{w}'] = cpp_bridge.rolling_mean(df_pl, col, window=w).to_numpy()
        features[f'{col}_std_{w}'] = cpp_bridge.rolling_std(df_pl, col, window=w).to_numpy()
        features[f'{col}_zscore_{w}'] = cpp_bridge.rolling_zscore(df_pl, col, window=w).to_numpy()

    return pd.DataFrame(features)


def compute_technical_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute technical indicators using C++ kernels."""
    print("Computing technical features...")

    features = {}

    # Convert pandas to polars for C++ bridge
    df_pl = pl.from_pandas(df)

    # EMAs
    for period in [7, 14, 21, 28, 50, 100, 200]:
        features[f'ema_{period}'] = cpp_bridge.ema(df_pl, 'close', period=period).to_numpy()

    # RSI
    for period in [7, 14, 21, 28]:
        features[f'rsi_{period}'] = cpp_bridge.rsi(df_pl, 'close', period=period).to_numpy()

    # ATR
    for period in [7, 14, 21, 28]:
        features[f'atr_{period}'] = cpp_bridge.atr(df_pl, period=period).to_numpy()

    # Bollinger bands
    bb = cpp_bridge.bollinger_bands(df_pl, 'close', period=20, num_std=2.0)
    for k, v in bb.items():
        features[k] = v.to_numpy()

    return pd.DataFrame(features)


def compute_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute time/calendar features."""
    print("Computing time features...")

    features = {
        'hour': df['time'].dt.hour,
        'weekday': df['time'].dt.weekday,
        'day': df['time'].dt.day,
        'month': df['time'].dt.month,
        'quarter': df['time'].dt.quarter,
    }

    return pd.DataFrame(features)


def compute_forward_returns(df: pd.DataFrame, horizons: list[int]) -> pd.DataFrame:
    """Compute forward return labels."""
    print("Computing forward return labels...")

    labels = {}

    for h in horizons:
        labels[f'fwd_ret_{h}'] = df['close'].pct_change(h).shift(-h)
        labels[f'fwd_dir_{h}'] = (labels[f'fwd_ret_{h}'] > 0).astype(float)

    return pd.DataFrame(labels)


def map_semantic_to_registry(df: pd.DataFrame, registry: HydraRegistry) -> tuple[pd.DataFrame, dict]:
    """Map semantic features into registry slots, replacing null placeholders."""
    print(f"Mapping semantic features into registry slots...")

    # Extract semantic columns
    semantic_cols = [c for c in df.columns if c.startswith('xau__')]
    print(f"  Found {len(semantic_cols)} semantic columns")

    # Generate registry slots
    from dominion.dataset.registries import BLOCK_ALLOCATIONS
    registry_slots = []
    for block_id, (count, _, _, _, _) in BLOCK_ALLOCATIONS.items():
        for i in range(count):
            registry_slots.append(f"{block_id}_{i:04d}")

    # Use Block B slots (tick microstructure - unavailable)
    # B_0000 to B_0194 = 195 slots
    available_slots = [s for s in registry_slots if s.startswith('B_')][:len(semantic_cols)]

    if len(available_slots) < len(semantic_cols):
        raise ValueError(f"Insufficient registry slots: need {len(semantic_cols)}, have {len(available_slots)}")

    # Create mapping
    mapping = {}
    for i, semantic_name in enumerate(semantic_cols):
        slot = available_slots[i]
        mapping[slot] = {
            "registry_slot": slot,
            "semantic_name": semantic_name,
            "original_placeholder_name": slot,
            "block_id": "B",
            "source": "m5_feature_expansion",
            "computation_function": semantic_name.split('__')[2] if '__' in semantic_name else "unknown",
            "is_trainable_feature": True,
            "point_in_time_rule": "rolling with min_periods=1, no future data",
            "notes": f"Replaced null Block B placeholder {slot} with M5 semantic feature"
        }

    # Rename semantic columns to registry slots
    rename_map = {semantic_cols[i]: available_slots[i] for i in range(len(semantic_cols))}
    df = df.rename(columns=rename_map)

    print(f"  Mapped {len(semantic_cols)} semantic features to Block B slots")
    return df, mapping


def pad_to_registry(df: pd.DataFrame, registry: HydraRegistry) -> pd.DataFrame:
    """Pad dataframe to exactly 3,000 columns."""
    print(f"Padding from {len(df.columns)-1} to 3,000 columns...")

    # Generate all expected column names from registry
    from dominion.dataset.registries import BLOCK_ALLOCATIONS
    expected_cols = []
    for block_id, (count, _, _, _, _) in BLOCK_ALLOCATIONS.items():
        for i in range(count):
            expected_cols.append(f"{block_id}_{i:04d}")

    # Add missing registry columns as nulls
    for col in expected_cols:
        if col not in df.columns and col != 'time':
            df[col] = np.nan

    # Final column order: time + exactly 3000 registry cols
    final_cols = ['time'] + expected_cols

    print(f"  Final: {len(final_cols)} columns (exact)")
    return df[final_cols]


def build_full_dataset(
    timeframe: str = "H1",
    output_path: str = "data/hydra_full_dataset.parquet",
    max_rows: int = None
) -> pd.DataFrame:
    """Build complete HYDRA dataset."""

    print("=" * 80)
    print("BUILDING FULL HYDRA DATASET")
    print("=" * 80)

    # Connect to DuckDB
    con = duckdb.connect('data/dominion.duckdb', read_only=True)

    # Load base OHLCV
    df = load_gold_ohlcv(con, timeframe=timeframe)

    if max_rows:
        df = df.tail(max_rows)
        print(f"Limited to last {max_rows} rows")

    # Block A: Raw OHLCV (5 cols)
    base_cols = ['time', 'open', 'high', 'low', 'close', 'volume']
    df = df[base_cols].copy()
    df.columns = ['time', 'A_open', 'A_high', 'A_low', 'A_close', 'A_volume']

    # M5 EXPANDED FEATURES (90+ semantic features)
    # Add expanded features if M5 timeframe
    if timeframe == 'M5':
        print("\n" + "=" * 80)
        print("M5 DETECTED — Adding expanded feature set")
        print("=" * 80)

        # Prepare for expansion (need original column names)
        df_for_expansion = df.rename(columns={
            'A_open': 'open',
            'A_high': 'high',
            'A_low': 'low',
            'A_close': 'close',
            'A_volume': 'volume'
        })

        # Add 90 semantic features
        df_expanded = add_all_expanded_features(df_for_expansion)

        # Restore A_ prefix for base cols
        df = df_expanded.rename(columns={
            'open': 'A_open',
            'high': 'A_high',
            'low': 'A_low',
            'close': 'A_close',
            'volume': 'A_volume'
        })

        print("\n" + "=" * 80)
        print(f"M5 EXPANSION COMPLETE: {len(df.columns)} total columns")
        print("=" * 80 + "\n")

    # Block C: Rolling features (63 cols)
    windows = [5, 10, 20, 30, 60, 120, 240]
    roll_close = compute_rolling_features(df, 'A_close', windows[:3])  # First 3 windows
    roll_high = compute_rolling_features(df, 'A_high', windows[:2])
    roll_low = compute_rolling_features(df, 'A_low', windows[:2])

    # Rename with C_ prefix
    roll_features = pd.concat([roll_close, roll_high, roll_low], axis=1)
    roll_features.columns = [f'C_{i:04d}' for i in range(len(roll_features.columns))]
    df = pd.concat([df, roll_features], axis=1)

    # Block D: Technical features (21 cols)
    tech_features = compute_technical_features(df.rename(columns={'A_close': 'close', 'A_high': 'high', 'A_low': 'low'}))
    tech_features.columns = [f'D_{i:04d}' for i in range(len(tech_features.columns))]
    df = pd.concat([df, tech_features], axis=1)

    # Block G: Time features (5 cols)
    time_features = compute_time_features(df)
    time_features.columns = [f'G_{i:04d}' for i in range(len(time_features.columns))]
    df = pd.concat([df, time_features], axis=1)

    # Join macro data (Block I)
    macro_df = load_macro(con)
    df = asof_join_safe(df, macro_df, on='time')

    # Rename macro columns to I_ prefix
    macro_cols = [c for c in df.columns if c.startswith('macro_')]
    for i, col in enumerate(macro_cols):
        df.rename(columns={col: f'I_{i:04d}'}, inplace=True)

    # Join COT data (Block Q)
    cot_df = load_cot(con)
    df = asof_join_safe(df, cot_df, on='time')

    # Rename COT columns to Q_ prefix
    cot_cols = [c for c in df.columns if c.startswith('cot_')]
    for i, col in enumerate(cot_cols):
        df.rename(columns={col: f'Q_{i:04d}'}, inplace=True)

    # Join regime data (Block H)
    regime_df = load_regime(con)
    df = asof_join_safe(df, regime_df, on='time')

    # Rename regime columns to H_ prefix
    regime_cols = [c for c in df.columns if c.startswith('regime_')]
    for i, col in enumerate(regime_cols):
        df.rename(columns={col: f'H_{i:04d}'}, inplace=True)

    # Block Z4: Labels (12 cols)
    horizons = [1, 5, 10, 15, 30, 60]
    labels = compute_forward_returns(df.rename(columns={'A_close': 'close'}), horizons)
    labels.columns = [f'Z4_{i:04d}' for i in range(len(labels.columns))]
    df = pd.concat([df, labels], axis=1)

    con.close()

    # Map semantic features to registry slots (if present)
    registry = HydraRegistry()
    semantic_cols = [c for c in df.columns if c.startswith('xau__')]
    mapping = {}
    if semantic_cols:
        df, mapping = map_semantic_to_registry(df, registry)

        # Save mapping
        mapping_path = Path("data/registry/semantic_column_mapping.json")
        mapping_path.parent.mkdir(parents=True, exist_ok=True)
        import json
        with open(mapping_path, 'w') as f:
            json.dump(mapping, f, indent=2)
        print(f"  Saved mapping to {mapping_path}")

    # Pad to full 3,000 columns
    df = pad_to_registry(df, registry)

    # Save
    print(f"\nSaving to {output_path}...")
    df.to_parquet(output_path, compression='snappy', index=False)

    # Verify
    print("\n" + "=" * 80)
    print("DATASET BUILT")
    print("=" * 80)
    print(f"Rows: {len(df)}")
    print(f"Columns: {len(df.columns)}")
    print(f"Size: {Path(output_path).stat().st_size / 1024 / 1024:.1f} MB")
    print(f"Date range: {df['time'].min()} to {df['time'].max()}")
    print(f"Non-null columns: {(df.notna().any()).sum()}")
    print(f"Null columns: {(df.isna().all()).sum()}")

    return df


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Build full HYDRA dataset')
    parser.add_argument('--timeframe', default='M5', choices=['M5', 'M15', 'H1', 'H4', 'D1'])
    parser.add_argument('--output', default='data/hydra_m5_dataset.parquet')
    parser.add_argument('--max-rows', type=int, default=None)
    parser.add_argument('--run-gates', action='store_true')
    parser.add_argument('--allow-smoke', action='store_true', help='Allow non-M5 timeframes for smoke testing')

    args = parser.parse_args()

    # Check timeframe
    if args.timeframe != 'M5' and not args.allow_smoke:
        print("ERROR: Non-M5 timeframe requires --allow-smoke flag")
        print(f"  Requested: {args.timeframe}")
        print(f"  Production target: M5")
        print(f"\nTo build smoke test dataset:")
        print(f"  python {sys.argv[0]} --timeframe {args.timeframe} --allow-smoke")
        sys.exit(1)

    if args.allow_smoke and args.timeframe != 'M5':
        print(f"⚠️  SMOKE TEST MODE: Using {args.timeframe} instead of M5")

    # Build dataset
    df = build_full_dataset(
        timeframe=args.timeframe,
        output_path=args.output,
        max_rows=args.max_rows
    )

    # Run quality gates
    if args.run_gates:
        print("\n" + "=" * 80)
        print("RUNNING QUALITY GATES")
        print("=" * 80)

        training_allowed, results = run_all_gates(df)
        print_gate_report(results)

        if training_allowed:
            print("\n✅ TRAINING ALLOWED")
        else:
            print("\n❌ TRAINING BLOCKED")
