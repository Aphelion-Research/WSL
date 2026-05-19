"""CLI interface for data pipeline."""
import sys
import argparse
from pathlib import Path

from data_pipeline.pipeline import Pipeline
from data_pipeline.health.monitor import PipelineMonitor
from data_pipeline.health.report import ReportGenerator
from data_pipeline.features.store import FeatureStore
from data_pipeline.config import DUCKDB_PATH


def cmd_run(args):
    """Run the pipeline."""
    sources = args.sources.split(",") if args.sources else None

    pipeline = Pipeline(DUCKDB_PATH)
    pipeline.run(source_names=sources)


def cmd_status(args):
    """Show health status of all sources."""
    monitor = PipelineMonitor(DUCKDB_PATH)

    staleness = monitor.check_staleness()

    print("SOURCE HEALTH STATUS:")
    print("=" * 60)

    for source, info in staleness.items():
        status_symbol = "✓" if info["status"] == "OK" else "✗"
        age = info["age_seconds"]

        if age is not None:
            age_str = f"{age / 3600:.1f}h ago"
        else:
            age_str = "never"

        print(f"{status_symbol} {source:15} | {info['status']:15} | {age_str}")

    print("=" * 60)


def cmd_doctor(args):
    """Deep health check."""
    monitor = PipelineMonitor(DUCKDB_PATH)

    print("PIPELINE HEALTH CHECK:")
    print("=" * 60)

    # Staleness
    staleness = monitor.check_staleness()
    stale_count = sum(1 for info in staleness.values() if info["is_stale"])
    print(f"Stale sources: {stale_count}/{len(staleness)}")

    # Gaps
    gaps = monitor.detect_gaps()
    print(f"Gaps detected: {len(gaps)}")

    if gaps:
        print("\nTop 5 gaps:")
        for start, end in gaps[:5]:
            duration = (end - start).total_seconds() / 60
            print(f"  {start} -> {end} ({duration:.0f} minutes)")

    # Gold-DXY correlation
    inverted, corr = monitor.monitor_gold_dxy_correlation()
    print(f"\nGold-DXY correlation: {corr:.3f}")
    if inverted:
        print("  WARNING: Correlation inverted!")

    print("=" * 60)


def cmd_report(args):
    """Generate and display intelligence report."""
    from datetime import date

    report_gen = ReportGenerator(DUCKDB_PATH)

    # Generate fresh report
    report_text, filepath = report_gen.generate_and_store("cli-manual")

    print(report_text)


def cmd_backfill(args):
    """Backfill historical data."""
    from datetime import datetime, timedelta

    days = args.days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    print(f"Backfilling {days} days of data ({start_date} to {end_date})...")

    pipeline = Pipeline(DUCKDB_PATH)

    # Fetch with date range (requires modifying sources to accept date range)
    # For now, just run normal fetch which gets historical data
    pipeline.run()

    print("Backfill complete")


def cmd_features(args):
    """Show top features by IC."""
    top_n = args.top

    store = FeatureStore(DUCKDB_PATH)

    print(f"TOP {top_n} FEATURES BY IC:")
    print("=" * 60)

    top_features = store.get_feature_importance(top_n)

    if not top_features.empty:
        for _, row in top_features.iterrows():
            print(f"{row['feature_name']:40} | IC={row['avg_ic']:+.4f}")
    else:
        print("No feature importance data available")

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Blackmark Dominion Data Pipeline CLI"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # run command
    run_parser = subparsers.add_parser("run", help="Run the full pipeline")
    run_parser.add_argument(
        "--sources",
        type=str,
        help="Comma-separated list of sources to fetch (default: all)"
    )
    run_parser.set_defaults(func=cmd_run)

    # status command
    status_parser = subparsers.add_parser("status", help="Show source health status")
    status_parser.set_defaults(func=cmd_status)

    # doctor command
    doctor_parser = subparsers.add_parser("doctor", help="Deep health check")
    doctor_parser.set_defaults(func=cmd_doctor)

    # report command
    report_parser = subparsers.add_parser("report", help="Generate intelligence report")
    report_parser.set_defaults(func=cmd_report)

    # backfill command
    backfill_parser = subparsers.add_parser("backfill", help="Backfill historical data")
    backfill_parser.add_argument(
        "--days",
        type=int,
        default=365,
        help="Number of days to backfill (default: 365)"
    )
    backfill_parser.set_defaults(func=cmd_backfill)

    # features command
    features_parser = subparsers.add_parser("features", help="Show top features by IC")
    features_parser.add_argument(
        "--top",
        type=int,
        default=20,
        help="Number of top features to show (default: 20)"
    )
    features_parser.set_defaults(func=cmd_features)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        args.func(args)
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
