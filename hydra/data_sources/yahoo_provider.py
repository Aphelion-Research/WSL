"""Yahoo provider — daily XAUUSD bars as swing-only fallback."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from hydra.data_sources.base import (
    DataProvider, CoverageReport, FetchResult, NormalizeResult, QualityReport,
)

CACHE_DIR = Path.home() / "Dominion" / "data" / "raw" / "provider=yahoo" / "symbol=XAUUSD"


class YahooProvider(DataProvider):
    name = "Yahoo"

    def probe(self, symbol: str, timeframe: str, start: datetime, end: datetime) -> CoverageReport:
        report = CoverageReport(
            provider=self.name, symbol=symbol, timeframe=timeframe,
            requested_start=start, requested_end=end,
        )

        # Yahoo only provides daily data reliably for gold
        if timeframe not in ("D1", "H4"):
            report.can_fetch = False
            report.reason_if_not = f"Yahoo only provides daily bars, cannot serve {timeframe}"
            return report

        # Check cached data
        cached = CACHE_DIR / f"{symbol}_D1_yahoo.parquet"
        if cached.exists():
            df = pd.read_parquet(cached)
            ts = pd.to_datetime(df["ts"])
            report.start_available = ts.min().to_pydatetime()
            report.end_available = ts.max().to_pydatetime()
            report.estimated_rows = len(df)
            requested_days = (end - start).days
            avail_days = (report.end_available - report.start_available).days
            report.coverage_pct = min(avail_days / requested_days * 100, 100) if requested_days > 0 else 0
            report.can_fetch = True
            report.quality_score = 0.7
            return report

        # Yahoo can serve ~20+ years of daily gold via GC=F or ^XAU
        report.can_fetch = True
        report.start_available = datetime(2004, 1, 1, tzinfo=timezone.utc)
        report.end_available = datetime.now(timezone.utc)
        requested_days = (end - start).days
        avail_days = (report.end_available - report.start_available).days
        report.coverage_pct = min(avail_days / requested_days * 100, 100) if requested_days > 0 else 0
        report.quality_score = 0.6  # Lower quality — no bid/ask, no spread
        return report

    def fetch(self, symbol: str, timeframe: str, start: datetime, end: datetime,
              output_dir: str) -> FetchResult:
        t0 = time.time()
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        if timeframe not in ("D1", "H4"):
            return FetchResult(
                provider=self.name, symbol=symbol, timeframe=timeframe,
                success=False, error=f"Yahoo cannot serve {timeframe}",
                elapsed_seconds=time.time() - t0,
            )

        try:
            import yfinance as yf
            ticker = yf.Ticker("GC=F")
            start_str = start.strftime("%Y-%m-%d")
            end_str = end.strftime("%Y-%m-%d")
            df = ticker.history(start=start_str, end=end_str, interval="1d")

            if df.empty:
                return FetchResult(
                    provider=self.name, symbol=symbol, timeframe=timeframe,
                    success=False, error="No data from Yahoo Finance",
                    elapsed_seconds=time.time() - t0,
                )

            df = df.reset_index()
            df = df.rename(columns={
                "Date": "ts", "Open": "open", "High": "high",
                "Low": "low", "Close": "close", "Volume": "volume",
            })
            df["ts"] = pd.to_datetime(df["ts"], utc=True)
            cols = [c for c in ["ts", "open", "high", "low", "close", "volume"] if c in df.columns]
            df = df[cols].sort_values("ts").reset_index(drop=True)

            out_path = out_dir / f"{symbol}_{timeframe}_yahoo.parquet"
            df.to_parquet(str(out_path), index=False)

            # Cache
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            df.to_parquet(str(CACHE_DIR / f"{symbol}_D1_yahoo.parquet"), index=False)

            return FetchResult(
                provider=self.name, symbol=symbol, timeframe=timeframe,
                success=True, rows_fetched=len(df), output_path=str(out_path),
                elapsed_seconds=time.time() - t0,
            )

        except ImportError:
            return FetchResult(
                provider=self.name, symbol=symbol, timeframe=timeframe,
                success=False, error="yfinance not installed. pip install yfinance",
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
            df["ts"] = pd.to_datetime(df["ts"], utc=True)
            df = df.sort_values("ts").drop_duplicates(subset=["ts"]).reset_index(drop=True)
            cols = [c for c in ["ts", "open", "high", "low", "close", "volume"] if c in df.columns]
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
            valid=sorted_ok and duplicates == 0,
            rows=len(df), duplicates=int(duplicates), nan_count=int(nans),
            bad_timestamps=0 if sorted_ok else 1,
            score=0.7 if sorted_ok else 0.3,
            notes="Yahoo daily only — no bid/ask, no spread, swing-only valid",
        )
