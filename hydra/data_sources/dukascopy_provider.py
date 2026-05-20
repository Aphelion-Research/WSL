"""Dukascopy provider — historical tick/minute data for XAUUSD.

Dukascopy provides free historical tick data via their CDN.
Format: bi5 compressed binary files per hour.
URL pattern: datafeed/XAUUSD/{YEAR}/{MONTH-1}/{DAY}/{HOUR}h_ticks.bi5
"""
from __future__ import annotations

import io
import lzma
import struct
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from hydra.data_sources.base import (
    DataProvider, CoverageReport, FetchResult, NormalizeResult, QualityReport,
)
from hydra.runtime_state import update_state, append_event

RAW_DIR = Path.home() / "Dominion" / "data" / "raw" / "provider=dukascopy" / "symbol=XAUUSD"
CANONICAL_DIR = Path.home() / "Dominion" / "data" / "canonical" / "provider=dukascopy" / "symbol=XAUUSD"

# Dukascopy serves data from ~2010 for gold
DUKASCOPY_START = datetime(2010, 1, 1, tzinfo=timezone.utc)
BASE_URL = "https://datafeed.dukascopy.com/datafeed/XAUUSD"

# bi5 tick record: 4 bytes time_ms (uint32), 4 bytes ask (uint32), 4 bytes bid (uint32),
#                  4 bytes ask_vol (float32), 4 bytes bid_vol (float32) = 20 bytes per tick
TICK_STRUCT = struct.Struct(">IIIff")
POINT_VALUE = 0.001  # for gold, prices stored as integers * 0.001


def _parse_bi5(data: bytes, base_dt: datetime) -> list[dict]:
    """Parse bi5 binary tick data."""
    records = []
    size = TICK_STRUCT.size
    for i in range(0, len(data) - size + 1, size):
        ms, ask_raw, bid_raw, ask_vol, bid_vol = TICK_STRUCT.unpack(data[i:i + size])
        ts = base_dt + timedelta(milliseconds=ms)
        ask = ask_raw * POINT_VALUE
        bid = bid_raw * POINT_VALUE
        records.append({
            "ts": ts, "bid": bid, "ask": ask,
            "bid_vol": bid_vol, "ask_vol": ask_vol,
        })
    return records


def _fetch_hour(dt: datetime, session=None) -> Optional[bytes]:
    """Fetch one hour of tick data from Dukascopy CDN."""
    import urllib.request
    year = dt.year
    month = dt.month - 1  # Dukascopy uses 0-indexed months
    day = dt.day
    hour = dt.hour
    url = f"{BASE_URL}/{year}/{month:02d}/{day:02d}/{hour:02d}h_ticks.bi5"

    try:
        if session:
            resp = session.get(url, timeout=30)
            if resp.status_code == 200 and len(resp.content) > 0:
                return lzma.decompress(resp.content)
            return None
        else:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                if len(raw) > 0:
                    return lzma.decompress(raw)
                return None
    except (lzma.LZMAError, Exception):
        return None


def _ticks_to_bars(ticks_df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """Resample tick data to OHLCV bars."""
    tf_map = {"M1": "1min", "M5": "5min", "M15": "15min", "H1": "1h", "H4": "4h", "D1": "1D"}
    freq = tf_map.get(timeframe)
    if not freq:
        raise ValueError(f"Unknown timeframe: {timeframe}")

    ticks_df = ticks_df.set_index("ts")
    mid = (ticks_df["bid"] + ticks_df["ask"]) / 2
    bars = mid.resample(freq).ohlc()
    bars.columns = ["open", "high", "low", "close"]
    bars["volume"] = ticks_df["bid_vol"].resample(freq).sum()
    bars["spread"] = (ticks_df["ask"] - ticks_df["bid"]).resample(freq).mean()
    bars = bars.dropna(subset=["open"])
    bars = bars.reset_index()
    bars.rename(columns={"ts": "ts"}, inplace=True)
    return bars


class DukascopyProvider(DataProvider):
    name = "Dukascopy"

    def __init__(self):
        self._session = None

    def _get_session(self):
        if self._session is None:
            try:
                import requests
                self._session = requests.Session()
                self._session.headers["User-Agent"] = "Mozilla/5.0"
            except ImportError:
                self._session = None
        return self._session

    def probe(self, symbol: str, timeframe: str, start: datetime, end: datetime) -> CoverageReport:
        report = CoverageReport(
            provider=self.name, symbol=symbol, timeframe=timeframe,
            requested_start=start, requested_end=end,
        )

        # Check if we already have cached canonical data
        tf_dir = CANONICAL_DIR / f"timeframe={timeframe}"
        if tf_dir.exists():
            parquets = sorted(tf_dir.glob("*.parquet"))
            if parquets:
                dfs = [pd.read_parquet(p) for p in parquets[:3] + parquets[-3:]]
                combined = pd.concat(dfs, ignore_index=True)
                ts = pd.to_datetime(combined["ts"])
                report.start_available = ts.min().to_pydatetime()
                report.end_available = ts.max().to_pydatetime()
                report.estimated_rows = len(parquets) * 1000  # rough estimate

                requested_days = (end - start).days
                avail_days = (report.end_available - report.start_available).days
                report.coverage_pct = min(avail_days / requested_days * 100, 100) if requested_days > 0 else 0
                report.can_fetch = True
                report.quality_score = 0.9
                return report

        # Dukascopy can serve from 2010
        duka_start = max(DUKASCOPY_START, start.replace(tzinfo=timezone.utc) if start.tzinfo is None else start)
        report.start_available = duka_start
        report.end_available = datetime.now(timezone.utc) - timedelta(days=1)

        requested_days = (end - start).days
        avail_days = (report.end_available - duka_start).days
        report.coverage_pct = min(avail_days / requested_days * 100, 100) if requested_days > 0 else 0
        report.can_fetch = True
        report.quality_score = 0.85
        report.reason_if_not = "" if report.can_fetch else "Dukascopy unavailable"
        return report

    def fetch(self, symbol: str, timeframe: str, start: datetime, end: datetime,
              output_dir: str, run_id: str = "") -> FetchResult:
        """Fetch tick data day by day, build bars for requested timeframe."""
        t0 = time.time()
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        start_utc = start.replace(tzinfo=timezone.utc) if start.tzinfo is None else start
        end_utc = end.replace(tzinfo=timezone.utc) if end.tzinfo is None else end
        start_utc = max(start_utc, DUKASCOPY_START)

        total_days = (end_utc - start_utc).days
        all_bars = []
        days_done = 0
        session = self._get_session()

        current = start_utc
        while current < end_utc:
            # Check for cached raw ticks for this day
            day_cache = RAW_DIR / f"timeframe=TICK" / f"date={current.strftime('%Y-%m-%d')}" / "ticks.parquet"

            if day_cache.exists():
                day_ticks = pd.read_parquet(day_cache)
            else:
                # Fetch 24 hours
                day_ticks_list = []
                for hour in range(24):
                    hour_dt = current.replace(hour=hour, minute=0, second=0, microsecond=0)
                    data = _fetch_hour(hour_dt, session)
                    if data:
                        records = _parse_bi5(data, hour_dt)
                        day_ticks_list.extend(records)
                    time.sleep(0.05)  # rate limiting

                if day_ticks_list:
                    day_ticks = pd.DataFrame(day_ticks_list)
                    # Cache raw ticks
                    day_cache.parent.mkdir(parents=True, exist_ok=True)
                    day_ticks.to_parquet(str(day_cache), index=False)
                else:
                    day_ticks = pd.DataFrame()

            if len(day_ticks) > 0:
                bars = _ticks_to_bars(day_ticks, timeframe)
                if len(bars) > 0:
                    all_bars.append(bars)

            days_done += 1
            current += timedelta(days=1)

            # Update progress every 10 days
            if days_done % 10 == 0:
                pct = (days_done / total_days) * 100 if total_days > 0 else 0
                update_state(
                    phase_progress_pct=pct,
                    current_task=f"Downloading {symbol} {timeframe} day {days_done}/{total_days}",
                    files_done=days_done, files_total=total_days,
                )
                if run_id:
                    append_event(run_id, "INFO", "DATA_DOWNLOAD", "day_complete",
                                 f"Downloaded {current.strftime('%Y-%m-%d')}, {days_done}/{total_days}")

        if not all_bars:
            return FetchResult(
                provider=self.name, symbol=symbol, timeframe=timeframe,
                success=False, error="No data retrieved from Dukascopy",
                elapsed_seconds=time.time() - t0,
            )

        combined = pd.concat(all_bars, ignore_index=True)
        combined = combined.sort_values("ts").drop_duplicates(subset=["ts"]).reset_index(drop=True)

        out_path = out_dir / f"{symbol}_{timeframe}_dukascopy.parquet"
        combined.to_parquet(str(out_path), index=False)

        # Also save to canonical dir
        canonical_tf_dir = CANONICAL_DIR / f"timeframe={timeframe}"
        canonical_tf_dir.mkdir(parents=True, exist_ok=True)
        combined.to_parquet(str(canonical_tf_dir / "all.parquet"), index=False)

        return FetchResult(
            provider=self.name, symbol=symbol, timeframe=timeframe,
            success=True, rows_fetched=len(combined), output_path=str(out_path),
            elapsed_seconds=time.time() - t0,
        )

    def normalize(self, raw_path: str, output_path: str) -> NormalizeResult:
        try:
            df = pd.read_parquet(raw_path)
            df["ts"] = pd.to_datetime(df["ts"], utc=True)
            df = df.sort_values("ts").drop_duplicates(subset=["ts"]).reset_index(drop=True)
            cols = [c for c in ["ts", "open", "high", "low", "close", "volume", "spread"] if c in df.columns]
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
