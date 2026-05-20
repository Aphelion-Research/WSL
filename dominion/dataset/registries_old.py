"""
HYDRA 3,000-column registry system.
Exact allocation: A-Z4 feature blocks with source/column/quality metadata.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal


class SourceStatus(Enum):
    """Data source availability status."""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    RESERVED = "reserved"
    DEGRADED = "degraded"


class FeatureType(Enum):
    """Feature computation type."""
    RAW = "raw"
    ROLLING = "rolling"
    TECHNICAL = "technical"
    MICROSTRUCTURE = "microstructure"
    STATISTICAL = "statistical"
    DERIVED = "derived"
    LABEL = "label"


@dataclass(frozen=True)
class ColumnSpec:
    """Single column specification."""
    name: str
    source: str
    feature_type: FeatureType
    source_status: SourceStatus
    dtype: Literal["float32", "float64", "int32", "int64", "bool"]
    nullable: bool
    description: str


class HydraRegistry:
    """
    HYDRA 3,000-column exact allocation registry.

    Block allocation:
    - A: Raw OHLCV (5 cols)
    - B: Tick-level microstructure (200 cols)
    - C: Rolling statistics (300 cols)
    - D: Technical indicators (250 cols)
    - E: Volatility features (150 cols)
    - F: Order flow proxies (100 cols)
    - G: Time/calendar features (50 cols)
    - H: Regime indicators (50 cols)
    - I: Macro/COT features (100 cols)
    - J: Cross-timeframe features (200 cols)
    - K: Microstructure II (150 cols)
    - L: Statistical properties (150 cols)
    - M: Autocorrelation features (100 cols)
    - N: Distribution features (100 cols)
    - O: Candle morphology (100 cols)
    - P: Spread/liquidity proxies (100 cols)
    - Q: Volume profile (100 cols)
    - R: Higher-order moments (100 cols)
    - S: Information-theoretic (100 cols)
    - T: Copula/tail features (100 cols)
    - U: Realized measures (100 cols)
    - V: Jump detection (75 cols)
    - W: Fractal/scaling (75 cols)
    - X: Cross-asset correlations (100 cols)
    - Y: Sentiment proxies (50 cols)
    - Z1: Reserved block 1 (150 cols)
    - Z2: Reserved block 2 (150 cols)
    - Z3: Reserved block 3 (150 cols)
    - Z4: Labels/targets (50 cols)

    Total: 3,000 columns exact.
    """

    def __init__(self):
        self._columns: list[ColumnSpec] = []
        self._build_registry()

    def _build_registry(self):
        """Build all 3,000 columns."""
        # Block A: Raw OHLCV (5)
        for name in ["open", "high", "low", "close", "volume"]:
            self._columns.append(ColumnSpec(
                name=f"A_{name}",
                source="mt5_h1",
                feature_type=FeatureType.RAW,
                source_status=SourceStatus.AVAILABLE,
                dtype="float32" if name != "volume" else "int64",
                nullable=False,
                description=f"H1 {name}"
            ))

        # Block B: Tick microstructure (200)
        self._add_block("B", 200, "tick_metrics", FeatureType.MICROSTRUCTURE,
                       SourceStatus.UNAVAILABLE, "Tick-level metrics (bid/ask/spread)")

        # Block C: Rolling statistics (300)
        block_c_start = len(self._columns)
        windows = [5, 10, 20, 30, 60, 120, 240]
        metrics = ["mean", "std", "min", "max", "z_score", "skew", "kurt"]
        for win in windows:
            for metric in metrics:
                for price in ["close", "high", "low", "volume"]:
                    if len(self._columns) - block_c_start >= 300:
                        break
                    self._columns.append(ColumnSpec(
                        name=f"C_roll_{win}_{metric}_{price}",
                        source="cpp_kernels",
                        feature_type=FeatureType.ROLLING,
                        source_status=SourceStatus.AVAILABLE,
                        dtype="float32",
                        nullable=True,
                        description=f"{win}-bar rolling {metric} of {price}"
                    ))
                if len(self._columns) - block_c_start >= 300:
                    break
            if len(self._columns) - block_c_start >= 300:
                break

        # Block D: Technical indicators (250)
        indicators = []
        for win in [7, 14, 21, 28, 50, 100, 200]:
            indicators.extend([
                f"D_ema_{win}", f"D_rsi_{win}", f"D_atr_{win}",
                f"D_bb_upper_{win}", f"D_bb_lower_{win}", f"D_bb_width_{win}",
                f"D_adx_{win}", f"D_cci_{win}", f"D_williams_{win}",
                f"D_roc_{win}"
            ])
        for name in indicators[:250]:
            self._columns.append(ColumnSpec(
                name=name,
                source="cpp_kernels",
                feature_type=FeatureType.TECHNICAL,
                source_status=SourceStatus.AVAILABLE,
                dtype="float32",
                nullable=True,
                description=f"Technical indicator {name}"
            ))

        # Block E: Volatility features (150)
        self._add_block("E", 150, "cpp_kernels", FeatureType.STATISTICAL,
                       SourceStatus.AVAILABLE, "Realized volatility measures")

        # Block F: Order flow proxies (100)
        self._add_block("F", 100, "lob_metrics", FeatureType.MICROSTRUCTURE,
                       SourceStatus.UNAVAILABLE, "Order flow imbalance proxies")

        # Block G: Time/calendar (50)
        for name in ["hour", "dow", "dom", "month", "quarter", "is_monday",
                    "is_friday", "is_month_end", "is_quarter_end", "us_session",
                    "eu_session", "asia_session"]:
            self._columns.append(ColumnSpec(
                name=f"G_{name}",
                source="derived",
                feature_type=FeatureType.DERIVED,
                source_status=SourceStatus.AVAILABLE,
                dtype="int32" if not name.startswith("is_") else "bool",
                nullable=False,
                description=f"Time feature: {name}"
            ))
        # Fill remaining G slots
        self._add_block("G", 38, "derived", FeatureType.DERIVED,
                       SourceStatus.AVAILABLE, "Additional time features", start_idx=12)

        # Block H: Regime indicators (50)
        self._add_block("H", 50, "regime_labels", FeatureType.DERIVED,
                       SourceStatus.AVAILABLE, "Macro/tactical regimes")

        # Block I: Macro/COT (100)
        self._add_block("I", 100, "macro_cot", FeatureType.RAW,
                       SourceStatus.AVAILABLE, "Macro series + COT")

        # Block J: Cross-timeframe (200)
        self._add_block("J", 200, "multi_tf", FeatureType.DERIVED,
                       SourceStatus.AVAILABLE, "D1/H4/H1/M15 alignment")

        # Block K: Microstructure II (150)
        self._add_block("K", 150, "execution_metrics", FeatureType.MICROSTRUCTURE,
                       SourceStatus.UNAVAILABLE, "Execution quality metrics")

        # Block L: Statistical properties (150)
        self._add_block("L", 150, "cpp_kernels", FeatureType.STATISTICAL,
                       SourceStatus.AVAILABLE, "Skew/kurt/quantiles")

        # Block M: Autocorrelation (100)
        for lag in range(1, 26):
            for price in ["close", "returns", "volume", "range"]:
                self._columns.append(ColumnSpec(
                    name=f"M_acf_{lag}_{price}",
                    source="cpp_kernels",
                    feature_type=FeatureType.STATISTICAL,
                    source_status=SourceStatus.AVAILABLE,
                    dtype="float32",
                    nullable=True,
                    description=f"Lag-{lag} autocorrelation of {price}"
                ))
                if len([c for c in self._columns if c.name.startswith("M_")]) >= 100:
                    break
            if len([c for c in self._columns if c.name.startswith("M_")]) >= 100:
                break

        # Block N: Distribution features (100)
        self._add_block("N", 100, "cpp_kernels", FeatureType.STATISTICAL,
                       SourceStatus.AVAILABLE, "Distribution moments/quantiles")

        # Block O: Candle morphology (100)
        for name in ["body_size", "wick_upper", "wick_lower", "body_ratio",
                    "range_pct", "close_loc", "is_doji", "is_hammer", "is_star",
                    "is_engulfing"]:
            self._columns.append(ColumnSpec(
                name=f"O_{name}",
                source="cpp_kernels",
                feature_type=FeatureType.TECHNICAL,
                source_status=SourceStatus.AVAILABLE,
                dtype="float32" if not name.startswith("is_") else "bool",
                nullable=False,
                description=f"Candle pattern: {name}"
            ))
        self._add_block("O", 90, "cpp_kernels", FeatureType.TECHNICAL,
                       SourceStatus.AVAILABLE, "Additional candle features", start_idx=10)

        # Block P: Spread/liquidity proxies (100)
        self._add_block("P", 100, "lob_snapshots", FeatureType.MICROSTRUCTURE,
                       SourceStatus.UNAVAILABLE, "Spread/depth proxies")

        # Block Q: Volume profile (100)
        self._add_block("Q", 100, "cpp_kernels", FeatureType.STATISTICAL,
                       SourceStatus.AVAILABLE, "Volume distribution features")

        # Block R: Higher-order moments (100)
        self._add_block("R", 100, "cpp_kernels", FeatureType.STATISTICAL,
                       SourceStatus.AVAILABLE, "Skew/kurt across windows")

        # Block S: Information-theoretic (100)
        self._add_block("S", 100, "cpp_kernels", FeatureType.STATISTICAL,
                       SourceStatus.AVAILABLE, "Entropy/mutual info")

        # Block T: Copula/tail (100)
        self._add_block("T", 100, "cpp_kernels", FeatureType.STATISTICAL,
                       SourceStatus.AVAILABLE, "Tail dependence features")

        # Block U: Realized measures (100)
        self._add_block("U", 100, "cpp_kernels", FeatureType.STATISTICAL,
                       SourceStatus.AVAILABLE, "Realized vol/skew/kurt")

        # Block V: Jump detection (75)
        self._add_block("V", 75, "cpp_kernels", FeatureType.STATISTICAL,
                       SourceStatus.AVAILABLE, "Jump indicators")

        # Block W: Fractal/scaling (75)
        self._add_block("W", 75, "cpp_kernels", FeatureType.STATISTICAL,
                       SourceStatus.AVAILABLE, "Hurst exponent/fractals")

        # Block X: Cross-asset correlations (100)
        self._add_block("X", 100, "cross_asset", FeatureType.DERIVED,
                       SourceStatus.UNAVAILABLE, "DXY/SPX/rates correlations")

        # Block Y: Sentiment proxies (50)
        self._add_block("Y", 50, "sentiment", FeatureType.DERIVED,
                       SourceStatus.UNAVAILABLE, "Sentiment indicators")

        # Block Z1-Z3: Reserved (150 each)
        self._add_block("Z1", 150, "reserved", FeatureType.DERIVED,
                       SourceStatus.RESERVED, "Reserved for future use")
        self._add_block("Z2", 150, "reserved", FeatureType.DERIVED,
                       SourceStatus.RESERVED, "Reserved for future use")
        self._add_block("Z3", 150, "reserved", FeatureType.DERIVED,
                       SourceStatus.RESERVED, "Reserved for future use")

        # Block Z4: Labels/targets (50)
        for horizon in [1, 5, 10, 15, 30, 60]:
            for label_type in ["ret", "dir", "vol"]:
                self._columns.append(ColumnSpec(
                    name=f"Z4_label_{horizon}b_{label_type}",
                    source="labels",
                    feature_type=FeatureType.LABEL,
                    source_status=SourceStatus.AVAILABLE,
                    dtype="float32",
                    nullable=True,
                    description=f"{horizon}-bar {label_type} label"
                ))
        # Fill remaining Z4
        remaining = 50 - len([c for c in self._columns if c.name.startswith("Z4_")])
        self._add_block("Z4", remaining, "labels", FeatureType.LABEL,
                       SourceStatus.AVAILABLE, "Additional labels",
                       start_idx=50-remaining)

        # Validate exact 3,000
        assert len(self._columns) == 3000, f"Expected 3000 columns, got {len(self._columns)}"

    def _add_block(self, prefix: str, count: int, source: str,
                   feature_type: FeatureType, source_status: SourceStatus,
                   description: str, start_idx: int = 0):
        """Add a block of columns with sequential numbering."""
        for i in range(count):
            self._columns.append(ColumnSpec(
                name=f"{prefix}_{start_idx + i:04d}",
                source=source,
                feature_type=feature_type,
                source_status=source_status,
                dtype="float32",
                nullable=True,
                description=f"{description} #{start_idx + i}"
            ))

    @property
    def columns(self) -> list[ColumnSpec]:
        """Get all 3,000 column specs."""
        return self._columns

    @property
    def column_names(self) -> list[str]:
        """Get all 3,000 column names."""
        return [c.name for c in self._columns]

    def get_available_columns(self) -> list[ColumnSpec]:
        """Get only available columns (trainable)."""
        return [c for c in self._columns if c.source_status == SourceStatus.AVAILABLE]

    def get_unavailable_columns(self) -> list[ColumnSpec]:
        """Get unavailable columns (placeholders)."""
        return [c for c in self._columns if c.source_status == SourceStatus.UNAVAILABLE]

    def get_reserved_columns(self) -> list[ColumnSpec]:
        """Get reserved columns (future use)."""
        return [c for c in self._columns if c.source_status == SourceStatus.RESERVED]

    def summary(self) -> dict:
        """Get registry summary."""
        return {
            "total_columns": len(self._columns),
            "available": len(self.get_available_columns()),
            "unavailable": len(self.get_unavailable_columns()),
            "reserved": len(self.get_reserved_columns()),
            "by_type": {
                ftype.value: len([c for c in self._columns if c.feature_type == ftype])
                for ftype in FeatureType
            },
            "by_source": {
                src: len([c for c in self._columns if c.source == src])
                for src in set(c.source for c in self._columns)
            }
        }


# Singleton instance
HYDRA_REGISTRY = HydraRegistry()
