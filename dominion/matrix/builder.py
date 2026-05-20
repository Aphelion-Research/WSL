"""
HYDRA 3,000-column matrix builder.
Materializes all features according to registry.
"""
from __future__ import annotations

from pathlib import Path

import polars as pl
import numpy as np

from dominion.dataset.registries import HYDRA_REGISTRY, SourceStatus
from dominion.features import cpp_bridge
from dominion.joins.point_in_time import multi_asof_join


class MatrixBuilder:
    """Builds HYDRA 3,000-column feature matrix."""

    def __init__(self, registry=HYDRA_REGISTRY):
        self.registry = registry

    def build(
        self,
        h1_data_path: str | Path,
        output_path: str | Path | None = None,
        max_rows: int | None = None
    ) -> pl.DataFrame:
        """
        Build complete 3,000-column matrix.

        Args:
            h1_data_path: Path to H1 OHLCV parquet
            output_path: Optional path to save result
            max_rows: Optional limit on rows (for testing)

        Returns:
            3,000-column DataFrame with time index
        """
        print("Loading H1 base data...")
        df = pl.scan_parquet(h1_data_path).collect()

        # Convert time to datetime if needed
        if df["time"].dtype != pl.Datetime:
            df = df.with_columns(
                pl.from_epoch("time", time_unit="s").alias("time")
            )

        if max_rows:
            df = df.tail(max_rows)

        print(f"Base data: {df.height} rows")

        # Initialize result with time + all 3,000 columns
        result = df.select("time").sort("time")

        # Keep base OHLCV separate for feature computation
        base_ohlcv = df.select(["open", "high", "low", "close", "tick_volume"])

        # Build each block
        print("Building Block A: Raw OHLCV...")
        result = self._add_block_a(result, base_ohlcv)

        print("Building Block B: Tick microstructure (unavailable)...")
        result = self._add_unavailable_block(result, "B")

        print("Building Block C: Rolling statistics...")
        result = self._add_block_c(result, base_ohlcv)

        print("Building Block D: Technical indicators...")
        result = self._add_block_d(result, base_ohlcv)

        print("Building Block E: Volatility features...")
        result = self._add_block_e(result, base_ohlcv)

        print("Building Block F: Order flow (unavailable)...")
        result = self._add_unavailable_block(result, "F")

        print("Building Block G: Time/calendar features...")
        result = self._add_block_g(result, df)

        print("Building Block H-Z3: Remaining blocks...")
        for block in ["H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S",
                     "T", "U", "V", "W", "X", "Y", "Z1", "Z2", "Z3"]:
            block_cols = [c for c in self.registry.columns if c.name.startswith(f"{block}_")]
            if block_cols and block_cols[0].source_status == SourceStatus.UNAVAILABLE:
                result = self._add_unavailable_block(result, block)
            elif block_cols and block_cols[0].source_status == SourceStatus.RESERVED:
                result = self._add_reserved_block(result, block)
            elif block_cols and block_cols[0].source_status == SourceStatus.AVAILABLE:
                result = self._add_placeholder_block(result, block)

        print("Building Block Z4: Labels/targets...")
        result = self._add_block_z4(result, base_ohlcv)

        # Validate shape
        expected_cols = 3001  # 3,000 features + time
        if result.width != expected_cols:
            raise ValueError(f"Expected {expected_cols} cols, got {result.width}")

        print(f"Matrix built: {result.height} rows x {result.width} cols")

        if output_path:
            print(f"Saving to {output_path}...")
            result.write_parquet(output_path)

        return result

    def _add_block_a(self, result: pl.DataFrame, df: pl.DataFrame) -> pl.DataFrame:
        """Add Block A: Raw OHLCV (5 cols)."""
        return result.with_columns([
            df["open"].cast(pl.Float32).alias("A_open"),
            df["high"].cast(pl.Float32).alias("A_high"),
            df["low"].cast(pl.Float32).alias("A_low"),
            df["close"].cast(pl.Float32).alias("A_close"),
            df["tick_volume"].cast(pl.Int64).alias("A_volume"),
        ])

    def _add_block_c(self, result: pl.DataFrame, df: pl.DataFrame) -> pl.DataFrame:
        """Add Block C: Rolling statistics (300 cols)."""
        block_cols = [c for c in self.registry.columns if c.name.startswith("C_")]

        # Build some features using C++ kernels (sequential naming: C_0000, C_0001, etc.)
        features = []
        idx = 0
        windows = [5, 10, 20, 30, 60, 120, 240]

        for win in windows:
            for price in ["close", "high", "low"]:
                if idx < len(block_cols):
                    features.append(cpp_bridge.rolling_mean(df, price, win, name=f"C_{idx:04d}"))
                    idx += 1
                if idx < len(block_cols):
                    features.append(cpp_bridge.rolling_std(df, price, win, name=f"C_{idx:04d}"))
                    idx += 1
                if idx < len(block_cols):
                    features.append(cpp_bridge.rolling_zscore(df, price, win, name=f"C_{idx:04d}"))
                    idx += 1

        # Add computed features
        result = result.with_columns(features)

        # Fill remaining block C columns with nulls
        computed_names = {f.name for f in features}
        for col in block_cols:
            if col.name not in computed_names:
                result = result.with_columns(
                    pl.lit(None, dtype=pl.Float32).alias(col.name)
                )

        return result

    def _add_block_d(self, result: pl.DataFrame, df: pl.DataFrame) -> pl.DataFrame:
        """Add Block D: Technical indicators (250 cols)."""
        block_cols = [c for c in self.registry.columns if c.name.startswith("D_")]

        features = []
        idx = 0
        windows = [7, 14, 21, 28, 50, 100, 200]

        for win in windows:
            if idx < len(block_cols):
                features.append(cpp_bridge.ema(df, "close", win, name=f"D_{idx:04d}"))
                idx += 1
            if idx < len(block_cols):
                features.append(cpp_bridge.rsi(df, "close", win, name=f"D_{idx:04d}"))
                idx += 1
            if idx < len(block_cols):
                features.append(cpp_bridge.atr(df, win, name=f"D_{idx:04d}"))
                idx += 1

        result = result.with_columns(features)

        # Fill remaining with nulls
        computed_names = {f.name for f in features}
        for col in block_cols:
            if col.name not in computed_names:
                result = result.with_columns(
                    pl.lit(None, dtype=pl.Float32).alias(col.name)
                )

        return result

    def _add_block_e(self, result: pl.DataFrame, df: pl.DataFrame) -> pl.DataFrame:
        """Add Block E: Volatility features (150 cols)."""
        block_cols = [c for c in self.registry.columns if c.name.startswith("E_")]

        # Placeholder: fill with nulls
        for col in block_cols:
            result = result.with_columns(
                pl.lit(None, dtype=pl.Float32).alias(col.name)
            )

        return result

    def _add_block_g(self, result: pl.DataFrame, df: pl.DataFrame) -> pl.DataFrame:
        """Add Block G: Time/calendar features (50 cols)."""
        block_cols = [c for c in self.registry.columns if c.name.startswith("G_")]

        # Add a few actual time features with sequential naming
        features = [
            pl.col("time").dt.hour().cast(pl.Float32).alias("G_0000"),
            pl.col("time").dt.weekday().cast(pl.Float32).alias("G_0001"),
            pl.col("time").dt.day().cast(pl.Float32).alias("G_0002"),
            pl.col("time").dt.month().cast(pl.Float32).alias("G_0003"),
            pl.col("time").dt.quarter().cast(pl.Float32).alias("G_0004"),
        ]

        result = result.with_columns(features)

        # Fill remaining G columns with nulls
        computed_names = {"G_0000", "G_0001", "G_0002", "G_0003", "G_0004"}
        for col in block_cols:
            if col.name not in computed_names:
                result = result.with_columns(
                    pl.lit(None, dtype=pl.Float32).alias(col.name)
                )

        return result

    def _add_block_z4(self, result: pl.DataFrame, df: pl.DataFrame) -> pl.DataFrame:
        """Add Block Z4: Labels/targets (50 cols)."""
        block_cols = [c for c in self.registry.columns if c.name.startswith("Z4_")]

        # Compute forward returns (sequential naming: Z4_0000, Z4_0001, etc.)
        close = df["close"]
        labels = []
        idx = 0

        for horizon in [1, 5, 10, 15, 30, 60]:
            if idx < len(block_cols):
                # Forward return (shift negative for lookahead)
                fwd_ret = ((close.shift(-horizon) - close) / close).cast(pl.Float32).alias(f"Z4_{idx:04d}")
                labels.append(fwd_ret)
                idx += 1

            if idx < len(block_cols):
                # Forward direction
                fwd_dir = ((close.shift(-horizon) - close) > 0).cast(pl.Float32).alias(f"Z4_{idx:04d}")
                labels.append(fwd_dir)
                idx += 1

        result = result.with_columns(labels)

        # Fill remaining with nulls
        computed_names = {f"Z4_{i:04d}" for i in range(idx)}
        for col in block_cols:
            if col.name not in computed_names:
                result = result.with_columns(
                    pl.lit(None, dtype=pl.Float32).alias(col.name)
                )

        return result

    def _add_unavailable_block(self, result: pl.DataFrame, block: str) -> pl.DataFrame:
        """Add unavailable block (all nulls)."""
        block_cols = [c for c in self.registry.columns if c.name.startswith(f"{block}_")]
        for col in block_cols:
            result = result.with_columns(
                pl.lit(None, dtype=pl.Float32).alias(col.name)
            )
        return result

    def _add_reserved_block(self, result: pl.DataFrame, block: str) -> pl.DataFrame:
        """Add reserved block (all nulls with reserved marker)."""
        block_cols = [c for c in self.registry.columns if c.name.startswith(f"{block}_")]
        for col in block_cols:
            result = result.with_columns(
                pl.lit(None, dtype=pl.Float32).alias(col.name)
            )
        return result

    def _add_placeholder_block(self, result: pl.DataFrame, block: str) -> pl.DataFrame:
        """Add placeholder block (all nulls - to be implemented)."""
        block_cols = [c for c in self.registry.columns if c.name.startswith(f"{block}_")]
        for col in block_cols:
            dtype_map = {
                "float32": pl.Float32,
                "float64": pl.Float64,
                "int32": pl.Int32,
                "int64": pl.Int64,
                "bool": pl.Boolean,
            }
            dtype = dtype_map.get(col.dtype, pl.Float32)
            result = result.with_columns(
                pl.lit(None, dtype=dtype).alias(col.name)
            )
        return result


def build_hydra_matrix(
    h1_data_path: str = "/home/Martin/Dominion/data/mt5_history/XAUUSD_H1.parquet",
    output_path: str = "/home/Martin/Dominion/data/hydra_matrix.parquet",
    max_rows: int | None = None
) -> pl.DataFrame:
    """
    Convenience function to build HYDRA matrix.

    Args:
        h1_data_path: Path to H1 OHLCV data
        output_path: Path to save matrix
        max_rows: Optional row limit for testing

    Returns:
        3,000-column matrix
    """
    builder = MatrixBuilder()
    return builder.build(h1_data_path, output_path, max_rows)
