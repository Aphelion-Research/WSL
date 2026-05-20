"""MT5 provider — fetches historical bars via Wine/MT5 bridge."""
from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

from hydra.data_sources.base import (
    DataProvider, CoverageReport, FetchResult, NormalizeResult, QualityReport,
)

MT5_HISTORY_DIR = Path.home() / "Dominion" / "data" / "mt5_history"
SYMBOL_ALIASES = ["XAUUSD", "XAUUSD.", "GOLD", "GOLD.", "XAU/USD"]

TF_BARS_PER_DAY = {
    "M1": 1440, "M5": 288, "M15": 96, "H1": 24, "H4": 6, "D1": 1,
}


class MT5Provider(DataProvider):
    name = "MT5"

    def probe(self, symbol: str, timeframe: str, start: datetime, end: datetime) -> CoverageReport:
        report = CoverageReport(
            provider=self.name, symbol=symbol, timeframe=timeframe,
            requested_start=start, requested_end=end,
        )

        # Check if we have downloaded parquet data
        parquet_path = MT5_HISTORY_DIR / f"{symbol}_{timeframe}.parquet"
        json_meta = MT5_HISTORY_DIR / f"{symbol}_{timeframe}.json"

        if not parquet_path.exists():
            report.reason_if_not = f"No local MT5 data for {symbol} {timeframe}"
            report.can_fetch = self._can_attempt_fetch()
            return report

        try:
            df = pd.read_parquet(parquet_path)
            if "timestamp" in df.columns:
                ts = pd.to_datetime(df["timestamp"], utc=True)
            elif "time" in df.columns:
                ts = pd.to_datetime(df["time"], unit="s", utc=True)
            else:
                report.reason_if_not = "No timestamp column found"
                return report

            # Ensure tz-aware
            if ts.dt.tz is None:
                ts = ts.dt.tz_localize("UTC")

            report.start_available = ts.min().to_pydatetime()
            report.end_available = ts.max().to_pydatetime()
            report.estimated_rows = len(df)

            requested_days = (end - start).days
            if requested_days > 0:
                start_utc = pd.Timestamp(start).tz_localize("UTC") if pd.Timestamp(start).tzinfo is None else pd.Timestamp(start)
                end_utc = pd.Timestamp(end).tz_localize("UTC") if pd.Timestamp(end).tzinfo is None else pd.Timestamp(end)
                overlap_start = max(start_utc, ts.min())
                overlap_end = min(end_utc, ts.max())
                if overlap_end > overlap_start:
                    report.coverage_pct = ((overlap_end - overlap_start).days / requested_days) * 100
                else:
                    report.coverage_pct = 0.0

            report.can_fetch = report.coverage_pct >= 90
            if not report.can_fetch:
                report.reason_if_not = f"Only {report.coverage_pct:.1f}% coverage"
            report.quality_score = min(report.coverage_pct, 100) / 100.0

        except Exception as e:
            report.reason_if_not = f"Error reading parquet: {e}"

        return report

    def _can_attempt_fetch(self) -> bool:
        """Check if MT5 Wine bridge is available."""
        import shutil
        return shutil.which("wine") is not None

    def fetch(self, symbol: str, timeframe: str, start: datetime, end: datetime,
              output_dir: str) -> FetchResult:
        t0 = time.time()

        # Try to use existing downloaded data first
        parquet_path = MT5_HISTORY_DIR / f"{symbol}_{timeframe}.parquet"
        if parquet_path.exists():
            out_path = Path(output_dir) / f"{symbol}_{timeframe}_mt5.parquet"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            import shutil
            shutil.copy2(str(parquet_path), str(out_path))
            df = pd.read_parquet(out_path)
            return FetchResult(
                provider=self.name, symbol=symbol, timeframe=timeframe,
                success=True, rows_fetched=len(df), output_path=str(out_path),
                elapsed_seconds=time.time() - t0,
            )

        # Attempt live fetch via Wine
        if not self._can_attempt_fetch():
            return FetchResult(
                provider=self.name, symbol=symbol, timeframe=timeframe,
                success=False, error="Wine not available for MT5 fetch",
                elapsed_seconds=time.time() - t0,
            )

        # Delegate to existing download script
        import subprocess
        try:
            result = subprocess.run(
                ["python", "-c", f"""
import sys; sys.path.insert(0, '{Path.home() / "Dominion"}')
from hydra.download_mt5_history import fetch_timeframe, convert_to_parquet
r = fetch_timeframe('{timeframe}')
if 'error' not in r:
    convert_to_parquet('{timeframe}')
    print('OK')
else:
    print(f"FAIL: {{r['error']}}")
"""],
                capture_output=True, text=True, timeout=300,
                env={**os.environ, "PYTHONUNBUFFERED": "1"},
            )
            if "OK" in result.stdout:
                parquet_path = MT5_HISTORY_DIR / f"{symbol}_{timeframe}.parquet"
                if parquet_path.exists():
                    out_path = Path(output_dir) / f"{symbol}_{timeframe}_mt5.parquet"
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    import shutil
                    shutil.copy2(str(parquet_path), str(out_path))
                    df = pd.read_parquet(out_path)
                    return FetchResult(
                        provider=self.name, symbol=symbol, timeframe=timeframe,
                        success=True, rows_fetched=len(df), output_path=str(out_path),
                        elapsed_seconds=time.time() - t0,
                    )
            return FetchResult(
                provider=self.name, symbol=symbol, timeframe=timeframe,
                success=False, error=result.stdout[:200] + result.stderr[:200],
                elapsed_seconds=time.time() - t0,
            )
        except Exception as e:
            return FetchResult(
                provider=self.name, symbol=symbol, timeframe=timeframe,
                success=False, error=str(e), elapsed_seconds=time.time() - t0,
            )

    def normalize(self, raw_path: str, output_path: str) -> NormalizeResult:
        try:
            df = pd.read_parquet(raw_path)
            if "time" in df.columns and "ts" not in df.columns:
                df["ts"] = pd.to_datetime(df["time"], unit="s", utc=True)
            elif "timestamp" in df.columns and "ts" not in df.columns:
                df["ts"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values("ts").drop_duplicates(subset=["ts"]).reset_index(drop=True)
            cols = ["ts", "open", "high", "low", "close"]
            if "volume" in df.columns:
                cols.append("volume")
            elif "tick_volume" in df.columns:
                df["volume"] = df["tick_volume"]
                cols.append("volume")
            if "spread" in df.columns:
                cols.append("spread")
            df[cols].to_parquet(output_path, index=False)
            return NormalizeResult(success=True, rows_output=len(df), output_path=output_path)
        except Exception as e:
            return NormalizeResult(success=False, error=str(e))

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
            valid=sorted_ok and duplicates == 0 and nans == 0,
            rows=len(df), duplicates=int(duplicates), nan_count=int(nans),
            bad_timestamps=0 if sorted_ok else 1,
            score=0.85 if (sorted_ok and nans == 0) else 0.4,
        )
