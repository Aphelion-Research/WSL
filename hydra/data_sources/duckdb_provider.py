"""DuckDB provider — reads from existing dominion.duckdb gold_master table."""
from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

import duckdb
import pandas as pd

from hydra.config import DB_PATH
from hydra.data_sources.base import (
    DataProvider, CoverageReport, FetchResult, NormalizeResult, QualityReport,
)


class DuckDBProvider(DataProvider):
    name = "DuckDB"

    def probe(self, symbol: str, timeframe: str, start: datetime, end: datetime) -> CoverageReport:
        report = CoverageReport(
            provider=self.name, symbol=symbol, timeframe=timeframe,
            requested_start=start, requested_end=end,
        )
        if not DB_PATH.exists():
            report.reason_if_not = "DuckDB file not found"
            return report

        try:
            con = duckdb.connect(str(DB_PATH), read_only=True)
            row = con.execute(
                "SELECT MIN(timestamp), MAX(timestamp), COUNT(*) FROM gold_master"
            ).fetchone()
            con.close()
        except Exception as e:
            report.reason_if_not = str(e)
            return report

        if not row or row[2] == 0:
            report.reason_if_not = "gold_master table empty"
            return report

        db_start = pd.Timestamp(row[0])
        db_end = pd.Timestamp(row[1])
        total_rows = row[2]

        report.start_available = db_start.to_pydatetime()
        report.end_available = db_end.to_pydatetime()
        report.estimated_rows = total_rows

        requested_days = (end - start).days
        available_days = (db_end - db_start).days
        if requested_days > 0:
            # Normalize tz for comparison
            s = pd.Timestamp(start).tz_localize(None)
            e = pd.Timestamp(end).tz_localize(None)
            ds = db_start.tz_localize(None) if db_start.tzinfo else db_start
            de = db_end.tz_localize(None) if db_end.tzinfo else db_end
            overlap_start = max(s, ds)
            overlap_end = min(e, de)
            if overlap_end > overlap_start:
                report.coverage_pct = ((overlap_end - overlap_start).days / requested_days) * 100
            else:
                report.coverage_pct = 0.0

        # DuckDB gold_master is daily bars
        if timeframe in ("M1", "M5", "M15"):
            report.can_fetch = False
            report.reason_if_not = f"DuckDB gold_master is daily-only, cannot provide {timeframe}"
        elif report.coverage_pct >= 90:
            report.can_fetch = True
        else:
            report.can_fetch = False
            report.reason_if_not = f"Coverage only {report.coverage_pct:.1f}%"

        report.quality_score = min(report.coverage_pct, 100) / 100.0
        return report

    def fetch(self, symbol: str, timeframe: str, start: datetime, end: datetime,
              output_dir: str) -> FetchResult:
        t0 = time.time()
        out_path = Path(output_dir) / f"{symbol}_{timeframe}_duckdb.parquet"
        out_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            con = duckdb.connect(str(DB_PATH), read_only=True)
            df = con.execute(
                "SELECT timestamp as ts, open, high, low, close, volume "
                "FROM gold_master WHERE timestamp >= ? AND timestamp <= ? ORDER BY timestamp",
                [start, end]
            ).df()
            con.close()
            df.to_parquet(str(out_path), index=False)
            return FetchResult(
                provider=self.name, symbol=symbol, timeframe=timeframe,
                success=True, rows_fetched=len(df), output_path=str(out_path),
                elapsed_seconds=time.time() - t0,
            )
        except Exception as e:
            return FetchResult(
                provider=self.name, symbol=symbol, timeframe=timeframe,
                success=False, error=str(e), elapsed_seconds=time.time() - t0,
            )

    def normalize(self, raw_path: str, output_path: str) -> NormalizeResult:
        # DuckDB output is already normalized
        import shutil
        shutil.copy2(raw_path, output_path)
        df = pd.read_parquet(raw_path)
        return NormalizeResult(success=True, rows_output=len(df), output_path=output_path)

    def validate(self, normalized_path: str) -> QualityReport:
        try:
            df = pd.read_parquet(normalized_path)
        except Exception as e:
            return QualityReport(valid=False, notes=str(e))

        ts = pd.to_datetime(df["ts"])
        duplicates = ts.duplicated().sum()
        nans = df[["open", "high", "low", "close"]].isna().sum().sum()
        sorted_ok = ts.is_monotonic_increasing

        return QualityReport(
            valid=sorted_ok and duplicates == 0,
            rows=len(df), duplicates=int(duplicates), nan_count=int(nans),
            bad_timestamps=0 if sorted_ok else 1,
            score=0.9 if sorted_ok else 0.5,
        )
