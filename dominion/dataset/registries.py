"""
Simplified HYDRA 3,000-column registry.
Uses sequential numbering to guarantee exact 3,000 columns.
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


# Exact allocation ensuring 3,000 total
BLOCK_ALLOCATIONS = {
    "A": (5, "mt5_h1", FeatureType.RAW, SourceStatus.AVAILABLE, "Raw OHLCV"),
    "B": (195, "tick_metrics", FeatureType.MICROSTRUCTURE, SourceStatus.UNAVAILABLE, "Tick microstructure"),
    "C": (300, "cpp_kernels", FeatureType.ROLLING, SourceStatus.AVAILABLE, "Rolling statistics"),
    "D": (250, "cpp_kernels", FeatureType.TECHNICAL, SourceStatus.AVAILABLE, "Technical indicators"),
    "E": (150, "cpp_kernels", FeatureType.STATISTICAL, SourceStatus.AVAILABLE, "Volatility features"),
    "F": (100, "lob_metrics", FeatureType.MICROSTRUCTURE, SourceStatus.UNAVAILABLE, "Order flow proxies"),
    "G": (50, "derived", FeatureType.DERIVED, SourceStatus.AVAILABLE, "Time/calendar features"),
    "H": (50, "regime_labels", FeatureType.DERIVED, SourceStatus.AVAILABLE, "Regime indicators"),
    "I": (100, "macro_cot", FeatureType.RAW, SourceStatus.AVAILABLE, "Macro/COT features"),
    "J": (200, "multi_tf", FeatureType.DERIVED, SourceStatus.AVAILABLE, "Cross-timeframe features"),
    "K": (150, "execution_metrics", FeatureType.MICROSTRUCTURE, SourceStatus.UNAVAILABLE, "Microstructure II"),
    "L": (150, "cpp_kernels", FeatureType.STATISTICAL, SourceStatus.AVAILABLE, "Statistical properties"),
    "M": (100, "cpp_kernels", FeatureType.STATISTICAL, SourceStatus.AVAILABLE, "Autocorrelation features"),
    "N": (100, "cpp_kernels", FeatureType.STATISTICAL, SourceStatus.AVAILABLE, "Distribution features"),
    "O": (100, "cpp_kernels", FeatureType.TECHNICAL, SourceStatus.AVAILABLE, "Candle morphology"),
    "P": (100, "lob_snapshots", FeatureType.MICROSTRUCTURE, SourceStatus.UNAVAILABLE, "Spread/liquidity"),
    "Q": (100, "cpp_kernels", FeatureType.STATISTICAL, SourceStatus.AVAILABLE, "Volume profile"),
    "R": (100, "cpp_kernels", FeatureType.STATISTICAL, SourceStatus.AVAILABLE, "Higher-order moments"),
    "S": (100, "cpp_kernels", FeatureType.STATISTICAL, SourceStatus.AVAILABLE, "Information-theoretic"),
    "T": (100, "cpp_kernels", FeatureType.STATISTICAL, SourceStatus.AVAILABLE, "Copula/tail features"),
    "U": (100, "cpp_kernels", FeatureType.STATISTICAL, SourceStatus.AVAILABLE, "Realized measures"),
    "V": (75, "cpp_kernels", FeatureType.STATISTICAL, SourceStatus.AVAILABLE, "Jump detection"),
    "W": (75, "cpp_kernels", FeatureType.STATISTICAL, SourceStatus.AVAILABLE, "Fractal/scaling"),
    "X": (100, "cross_asset", FeatureType.DERIVED, SourceStatus.UNAVAILABLE, "Cross-asset correlations"),
    "Y": (50, "sentiment", FeatureType.DERIVED, SourceStatus.UNAVAILABLE, "Sentiment proxies"),
    "Z1": (17, "reserved", FeatureType.DERIVED, SourceStatus.RESERVED, "Reserved block 1"),
    "Z2": (17, "reserved", FeatureType.DERIVED, SourceStatus.RESERVED, "Reserved block 2"),
    "Z3": (16, "reserved", FeatureType.DERIVED, SourceStatus.RESERVED, "Reserved block 3"),
    "Z4": (50, "labels", FeatureType.LABEL, SourceStatus.AVAILABLE, "Labels/targets"),
}


class HydraRegistry:
    """HYDRA 3,000-column exact allocation registry."""

    def __init__(self):
        self._columns: list[ColumnSpec] = []
        self._build_registry()

    def _build_registry(self):
        """Build all 3,000 columns with sequential numbering."""
        for block_name, (count, source, ftype, status, desc) in BLOCK_ALLOCATIONS.items():
            if block_name == "A":
                # Special case: named OHLCV columns
                for name in ["open", "high", "low", "close", "volume"]:
                    self._columns.append(ColumnSpec(
                        name=f"A_{name}",
                        source=source,
                        feature_type=ftype,
                        source_status=status,
                        dtype="float32" if name != "volume" else "int64",
                        nullable=False,
                        description=f"H1 {name}"
                    ))
            else:
                # Sequential numbering
                for i in range(count):
                    self._columns.append(ColumnSpec(
                        name=f"{block_name}_{i:04d}",
                        source=source,
                        feature_type=ftype,
                        source_status=status,
                        dtype="float32",
                        nullable=True,
                        description=f"{desc} #{i}"
                    ))

        # Validate exact 3,000
        assert len(self._columns) == 3000, f"Expected 3000 columns, got {len(self._columns)}"

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
