"""
Semantic naming convention for HYDRA features.

Format: {scope}__{family}__{signal}__{window}__{unit}

Examples:
  ohlcv__base__close__1__price
  rolling__stats__mean__60__bars
  technical__momentum__rsi__14__index
  macro__rates__10y__1__yield
  reserved__expansion__slot_001__none__null
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SemanticName:
    """Semantic name components."""
    scope: str      # ohlcv, rolling, technical, macro, etc
    family: str     # base, stats, momentum, rates, etc
    signal: str     # close, mean, rsi, 10y, etc
    window: str     # 1, 60, 14, etc (or "none")
    unit: str       # price, bars, index, yield, null, etc

    def to_string(self) -> str:
        """Convert to semantic name string."""
        return f"{self.scope}__{self.family}__{signal}__{self.window}__{self.unit}"

    @classmethod
    def from_string(cls, name: str) -> SemanticName:
        """Parse semantic name string."""
        parts = name.split("__")
        if len(parts) != 5:
            raise ValueError(f"Invalid semantic name: {name}")
        return cls(*parts)


def generate_ohlcv_names() -> list[str]:
    """Generate OHLCV semantic names (Block A)."""
    return [
        "ohlcv__base__open__1__price",
        "ohlcv__base__high__1__price",
        "ohlcv__base__low__1__price",
        "ohlcv__base__close__1__price",
        "ohlcv__base__volume__1__ticks",
    ]


def generate_rolling_names(windows: list[int], signals: list[str]) -> list[str]:
    """Generate rolling stat semantic names (Block C)."""
    names = []
    for window in windows:
        for signal in signals:
            for stat in ["mean", "std", "min", "max", "zscore"]:
                names.append(f"rolling__stats__{signal}_{stat}__{window}__bars")
    return names


def generate_technical_names(indicators: dict[str, list[int]]) -> list[str]:
    """Generate technical indicator semantic names (Block D)."""
    names = []
    for indicator, periods in indicators.items():
        for period in periods:
            if indicator == "ema":
                names.append(f"technical__trend__ema__{period}__price")
            elif indicator == "rsi":
                names.append(f"technical__momentum__rsi__{period}__index")
            elif indicator == "atr":
                names.append(f"technical__volatility__atr__{period}__price")
            elif indicator == "bb":
                for part in ["upper", "middle", "lower", "width"]:
                    names.append(f"technical__volatility__bb_{part}__{period}__price")
    return names


def generate_time_names() -> list[str]:
    """Generate time feature semantic names (Block G)."""
    return [
        "time__calendar__hour__1__utc",
        "time__calendar__weekday__1__index",
        "time__calendar__day__1__index",
        "time__calendar__month__1__index",
        "time__calendar__quarter__1__index",
    ]


def generate_macro_names(series: list[str]) -> list[str]:
    """Generate macro feature semantic names (Block I)."""
    names = []
    for s in series:
        names.append(f"macro__rates__{s}__1__value")
    return names


def generate_cot_names(fields: list[str]) -> list[str]:
    """Generate COT semantic names (Block Q)."""
    names = []
    for field in fields:
        names.append(f"positioning__cot__{field}__1__contracts")
    return names


def generate_regime_names(regimes: list[str]) -> list[str]:
    """Generate regime semantic names (Block H)."""
    names = [f"regime__state__{r}__1__binary" for r in regimes]
    names.append("regime__state__confidence__1__prob")
    return names


def generate_label_names(horizons: list[int]) -> list[str]:
    """Generate label semantic names (Block Z4)."""
    names = []
    for h in horizons:
        names.append(f"label__fwd_return__{h}bar__smoke__pct")
        names.append(f"label__fwd_direction__{h}bar__smoke__binary")
    return names


def generate_reserved_names(start: int, end: int) -> list[str]:
    """Generate reserved slot semantic names (Blocks Z1/Z2/Z3)."""
    return [
        f"reserved__expansion__slot_{i:03d}__none__null"
        for i in range(start, end + 1)
    ]


def generate_placeholder_names(block: str, start: int, end: int) -> list[str]:
    """Generate unavailable placeholder names."""
    return [
        f"unavailable__{block.lower()}__placeholder_{i:04d}__none__null"
        for i in range(start, end + 1)
    ]
