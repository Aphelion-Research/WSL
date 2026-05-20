"""Data Source Registry — audit, score, fetch, and validate across providers.

Usage:
    python -m hydra.data_sources.registry --audit --symbol XAUUSD --years 9
    python -m hydra.data_sources.registry --fetch-missing --symbol XAUUSD --years 9 --timeframes M1,M5,M15,H1,H4,D1
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from hydra.data_sources.base import CoverageReport
from hydra.data_sources.duckdb_provider import DuckDBProvider
from hydra.data_sources.mt5_provider import MT5Provider
from hydra.data_sources.dukascopy_provider import DukascopyProvider
from hydra.data_sources.yahoo_provider import YahooProvider
from hydra.runtime_state import (
    update_state, set_phase, set_idle, append_event, read_state,
)

RUNS_DIR = Path.home() / "Dominion" / "runs"
ALL_TIMEFRAMES = ["M1", "M5", "M15", "H1", "H4", "D1"]

# Provider priority order
PROVIDERS = [
    DuckDBProvider(),
    MT5Provider(),
    DukascopyProvider(),
    YahooProvider(),
]


def compute_date_range(years: int) -> tuple[datetime, datetime]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=int(years * 365.25 + 60))  # +60 warmup days
    return start, end


def run_audit(symbol: str, years: int, timeframes: list[str] | None = None,
              run_id: str = "", verbose: bool = True) -> dict:
    """Audit data availability across all providers for all timeframes."""
    if timeframes is None:
        timeframes = ALL_TIMEFRAMES

    start, end = compute_date_range(years)
    set_phase("DATA_AUDIT", f"Auditing {symbol} {years}yr coverage")

    results = {"symbol": symbol, "years": years, "start": str(start), "end": str(end),
               "timeframes": {}, "providers": {}, "valid_modes": [], "invalid_modes": []}

    # Audit each provider for each timeframe
    for provider in PROVIDERS:
        prov_results = {}
        for tf in timeframes:
            report = provider.probe(symbol, tf, start, end)
            prov_results[tf] = {
                "coverage_pct": report.coverage_pct,
                "rows": report.estimated_rows,
                "can_fetch": report.can_fetch,
                "start": str(report.start_available) if report.start_available else None,
                "end": str(report.end_available) if report.end_available else None,
                "reason": report.reason_if_not,
                "quality": report.quality_score,
            }

            # Update state
            prov_state = "valid" if report.coverage_pct >= 90 else (
                "insufficient" if report.coverage_pct > 0 else "failed"
            )
            update_state(**{f"providers.{provider.name}": {
                "status": prov_state,
                "coverage_pct": report.coverage_pct,
                "reason": report.reason_if_not,
            }})

        results["providers"][provider.name] = prov_results

    # Determine best provider per timeframe
    for tf in timeframes:
        best_provider = None
        best_coverage = 0
        best_quality = 0
        for provider in PROVIDERS:
            info = results["providers"][provider.name].get(tf, {})
            cov = info.get("coverage_pct", 0)
            qual = info.get("quality", 0)
            if cov > best_coverage or (cov == best_coverage and qual > best_quality):
                best_coverage = cov
                best_quality = qual
                best_provider = provider.name
        results["timeframes"][tf] = {
            "best_provider": best_provider,
            "best_coverage_pct": best_coverage,
            "sufficient": best_coverage >= 90,
            "can_fetch_from": [
                p.name for p in PROVIDERS
                if results["providers"][p.name].get(tf, {}).get("can_fetch")
            ],
        }

    # Determine valid modes
    m1_ok = results["timeframes"].get("M1", {}).get("sufficient", False)
    m5_ok = results["timeframes"].get("M5", {}).get("sufficient", False)
    m15_ok = results["timeframes"].get("M15", {}).get("sufficient", False)
    h1_ok = results["timeframes"].get("H1", {}).get("sufficient", False)
    h4_ok = results["timeframes"].get("H4", {}).get("sufficient", False)
    d1_ok = results["timeframes"].get("D1", {}).get("sufficient", False)

    if m1_ok or m5_ok:
        results["valid_modes"].append("scalp")
    else:
        results["invalid_modes"].append(("scalp", "Requires M1/M5 intraday data"))

    if m5_ok or m15_ok or h1_ok:
        results["valid_modes"].append("daytrade")
    else:
        results["invalid_modes"].append(("daytrade", "Requires M5/M15/H1 intraday data"))

    if h4_ok or d1_ok:
        results["valid_modes"].append("swing")
    else:
        results["invalid_modes"].append(("swing", "Requires H4/D1 data"))

    if results["valid_modes"]:
        results["valid_modes"].append("combined")

    # Update mode states
    for mode in ("scalp", "daytrade", "swing"):
        if mode in results["valid_modes"]:
            update_state(**{f"modes.{mode}": {"status": "pending", "reason": None,
                                              "progress_pct": 0, "best_validation_sharpe": None, "trades": 0}})
        else:
            reason = next((r for m, r in results["invalid_modes"] if m == mode), "")
            update_state(**{f"modes.{mode}": {"status": "invalid", "reason": reason,
                                              "progress_pct": 0, "best_validation_sharpe": None, "trades": 0}})

    if verbose:
        _print_audit(results)

    # Save report
    if run_id:
        report_dir = RUNS_DIR / run_id
        report_dir.mkdir(parents=True, exist_ok=True)
        with open(report_dir / "data_coverage.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        append_event(run_id, "INFO", "DATA_AUDIT", "audit_complete",
                     f"Audit complete: {len(results['valid_modes'])} valid modes")

    return results


def _print_audit(results: dict) -> None:
    print()
    print("=" * 70)
    print("  DATA AUDIT REPORT")
    print("=" * 70)
    print(f"  Symbol:          {results['symbol']}")
    print(f"  Requested years: {results['years']}")
    print(f"  Range:           {results['start']} → {results['end']}")
    print()

    print("  PROVIDER COVERAGE:")
    print("  " + "-" * 66)
    for pname, ptfs in results["providers"].items():
        print(f"  {pname}:")
        for tf, info in ptfs.items():
            status = "OK" if info["coverage_pct"] >= 90 else "INSUFFICIENT" if info["coverage_pct"] > 0 else "NONE"
            print(f"    {tf:4s}: {info['coverage_pct']:5.1f}% | {info['rows']:>10,} rows | {status}")
            if info.get("reason"):
                print(f"          → {info['reason']}")
        print()

    print("  TIMEFRAME SUMMARY:")
    print("  " + "-" * 66)
    for tf, info in results["timeframes"].items():
        suf = "✓" if info["sufficient"] else "✗"
        print(f"    {tf:4s}: {suf} {info['best_coverage_pct']:5.1f}% via {info['best_provider'] or 'NONE'}")
        if info["can_fetch_from"]:
            print(f"          Can fetch from: {', '.join(info['can_fetch_from'])}")
    print()

    print("  MODE VALIDITY:")
    print("  " + "-" * 66)
    for mode in results["valid_modes"]:
        print(f"    ✓ {mode.upper()}")
    for mode, reason in results["invalid_modes"]:
        print(f"    ✗ {mode.upper()}: {reason}")
    print()
    print("=" * 70)


def fetch_missing(symbol: str, years: int, timeframes: list[str],
                  run_id: str = "") -> dict:
    """Identify and fetch missing data from best available providers."""
    set_phase("DATA_DOWNLOAD", f"Fetching missing {symbol} data")

    # First audit
    audit = run_audit(symbol, years, timeframes, run_id=run_id, verbose=False)
    start, end = compute_date_range(years)

    fetch_results = {}
    total_tfs = len(timeframes)

    for i, tf in enumerate(timeframes):
        tf_info = audit["timeframes"].get(tf, {})
        if tf_info.get("sufficient"):
            print(f"  {tf}: Already sufficient ({tf_info['best_coverage_pct']:.1f}%)")
            fetch_results[tf] = {"status": "already_sufficient", "provider": tf_info["best_provider"]}
            continue

        # Try providers in order
        fetched = False
        can_fetch = tf_info.get("can_fetch_from", [])
        for provider in PROVIDERS:
            if provider.name not in can_fetch:
                continue

            print(f"  {tf}: Fetching from {provider.name}...", flush=True)
            update_state(
                provider=provider.name, timeframe=tf,
                current_task=f"Fetching {symbol} {tf} from {provider.name}",
                phase_progress_pct=(i / total_tfs) * 100,
            )

            out_dir = str(Path.home() / "Dominion" / "data" / "fetched" / f"{symbol}_{tf}")
            if hasattr(provider, 'fetch') and 'run_id' in provider.fetch.__code__.co_varnames:
                result = provider.fetch(symbol, tf, start, end, out_dir, run_id=run_id)
            else:
                result = provider.fetch(symbol, tf, start, end, out_dir)

            if result.success:
                print(f"    → OK: {result.rows_fetched:,} rows in {result.elapsed_seconds:.1f}s")
                fetch_results[tf] = {
                    "status": "fetched", "provider": provider.name,
                    "rows": result.rows_fetched, "path": result.output_path,
                }
                if run_id:
                    append_event(run_id, "SUCCESS", "DATA_DOWNLOAD", "fetch_complete",
                                 f"{tf} fetched from {provider.name}: {result.rows_fetched:,} rows")
                fetched = True
                break
            else:
                print(f"    → FAILED: {result.error[:100]}")
                if run_id:
                    append_event(run_id, "WARNING", "DATA_DOWNLOAD", "fetch_failed",
                                 f"{tf} from {provider.name}: {result.error[:100]}")

        if not fetched:
            print(f"  {tf}: NO PROVIDER COULD SERVE THIS TIMEFRAME")
            fetch_results[tf] = {"status": "unavailable", "reason": "All providers failed"}

    # Re-audit after fetch
    print("\n  Re-auditing after fetch...")
    final_audit = run_audit(symbol, years, timeframes, run_id=run_id, verbose=True)

    return {"fetch_results": fetch_results, "final_audit": final_audit}


def main():
    parser = argparse.ArgumentParser(description="HYDRA Data Source Registry")
    parser.add_argument("--audit", action="store_true", help="Run data audit")
    parser.add_argument("--fetch-missing", action="store_true", help="Fetch missing data")
    parser.add_argument("--symbol", default="XAUUSD", help="Symbol")
    parser.add_argument("--years", type=int, default=9, help="Required years")
    parser.add_argument("--timeframes", default="M1,M5,M15,H1,H4,D1", help="Comma-separated timeframes")
    args = parser.parse_args()

    timeframes = [t.strip() for t in args.timeframes.split(",")]
    run_id = f"hydra_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    if args.audit:
        run_audit(args.symbol, args.years, timeframes, run_id=run_id)
    elif args.fetch_missing:
        fetch_missing(args.symbol, args.years, timeframes, run_id=run_id)
    else:
        parser.print_help()

    set_idle()


if __name__ == "__main__":
    main()
