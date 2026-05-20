"""Base data provider interface and report dataclasses."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class CoverageReport:
    provider: str
    symbol: str
    timeframe: str
    requested_start: datetime
    requested_end: datetime
    start_available: Optional[datetime] = None
    end_available: Optional[datetime] = None
    coverage_pct: float = 0.0
    estimated_rows: int = 0
    missing_ranges: list = field(default_factory=list)
    duplicate_pct: float = 0.0
    nan_pct: float = 0.0
    bad_timestamp_pct: float = 0.0
    quality_score: float = 0.0
    can_fetch: bool = False
    reason_if_not: str = ""


@dataclass
class FetchResult:
    provider: str
    symbol: str
    timeframe: str
    success: bool
    rows_fetched: int = 0
    output_path: str = ""
    error: str = ""
    elapsed_seconds: float = 0.0


@dataclass
class NormalizeResult:
    success: bool
    rows_output: int = 0
    output_path: str = ""
    error: str = ""


@dataclass
class QualityReport:
    valid: bool
    rows: int = 0
    duplicates: int = 0
    nan_count: int = 0
    bad_timestamps: int = 0
    gaps: list = field(default_factory=list)
    score: float = 0.0
    notes: str = ""


class DataProvider:
    name: str = "base"

    def probe(self, symbol: str, timeframe: str, start: datetime, end: datetime) -> CoverageReport:
        raise NotImplementedError

    def fetch(self, symbol: str, timeframe: str, start: datetime, end: datetime,
              output_dir: str) -> FetchResult:
        raise NotImplementedError

    def normalize(self, raw_path: str, output_path: str) -> NormalizeResult:
        raise NotImplementedError

    def validate(self, normalized_path: str) -> QualityReport:
        raise NotImplementedError
