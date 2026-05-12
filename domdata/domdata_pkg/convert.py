from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _require_polars():
    try:
        import polars as pl  # type: ignore
    except Exception as exc:
        raise SystemExit(f"polars is required for conversion in the Linux venv: {exc!r}")
    return pl


def _require_duckdb():
    try:
        import duckdb  # type: ignore
    except Exception as exc:
        raise SystemExit(f"duckdb is required for local summaries in the Linux venv: {exc!r}")
    return duckdb


def _root(value: str) -> Path:
    return Path(value).expanduser().resolve()


def _read_jsonl(paths: list[Path]):
    pl = _require_polars()
    if not paths:
        return pl.DataFrame()
    return pl.concat([pl.read_ndjson(str(path)) for path in paths], how="diagonal_relaxed")


def _write_parquet(df: Any, path: Path) -> int:
    if df.is_empty():
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(str(path))
    return df.height


def convert_xau(args: Any) -> None:
    pl = _require_polars()
    date = args.date
    raw_root = _root(args.raw_root)
    out_root = _root(args.out_root)
    tick_paths = sorted((raw_root / "xauusd" / "ticks" / f"date={date}").glob("ticks-*.jsonl"))
    bar_paths = sorted((raw_root / "xauusd" / "bars" / "timeframe=M1" / f"date={date}").glob("bars-*.jsonl"))

    ticks = _read_jsonl(tick_paths)
    bars = _read_jsonl(bar_paths)
    tick_rows = 0
    bar_rows = 0

    if not ticks.is_empty():
        ticks = (
            ticks.unique(subset=["time_msc", "bid", "ask"], keep="first")
            .sort("time_msc")
            .with_columns(
                [
                    ((pl.col("bid") + pl.col("ask")) / 2).alias("mid"),
                    (pl.col("ask") - pl.col("bid")).alias("spread"),
                    ((pl.col("ask") - pl.col("bid")) / 0.001).alias("spread_points"),
                    pl.col("bid").diff().alias("bid_delta"),
                    pl.col("ask").diff().alias("ask_delta"),
                    (((pl.col("bid") + pl.col("ask")) / 2).diff()).alias("mid_delta"),
                    pl.col("time_msc").diff().alias("ms_since_prev_tick"),
                ]
            )
        )
        tick_rows = _write_parquet(ticks, out_root / "xauusd" / "ticks" / f"date={date}" / "ticks.parquet")

    if not bars.is_empty():
        bars = bars.unique(subset=["time"], keep="first").sort("time")
        bar_rows = _write_parquet(bars, out_root / "xauusd" / "bars" / "timeframe=M1" / f"date={date}" / "bars.parquet")

    print(f"convert-xau date={date} raw_ticks_files={len(tick_paths)} raw_bar_files={len(bar_paths)} tick_rows={tick_rows} bar_rows={bar_rows}")


def duckdb_init(args: Any) -> None:
    duckdb = _require_duckdb()
    db_path = _root(args.db)
    normalized_root = _root(args.normalized_root)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    try:
        con.execute("CREATE SCHEMA IF NOT EXISTS mt5")
        tick_files = list((normalized_root / "xauusd" / "ticks").glob("date=*/*.parquet"))
        bar_files = list((normalized_root / "xauusd" / "bars" / "timeframe=M1").glob("date=*/*.parquet"))
        if tick_files:
            pattern = str(normalized_root / "xauusd" / "ticks" / "date=*" / "*.parquet")
            con.execute(f"CREATE OR REPLACE VIEW mt5.xauusd_ticks AS SELECT * FROM read_parquet('{pattern}', hive_partitioning=true, union_by_name=true)")
        else:
            con.execute("CREATE OR REPLACE TABLE mt5.xauusd_ticks_empty(symbol VARCHAR, time_msc BIGINT, bid DOUBLE, ask DOUBLE, mid DOUBLE, spread DOUBLE)")
        if bar_files:
            pattern = str(normalized_root / "xauusd" / "bars" / "timeframe=M1" / "date=*" / "*.parquet")
            con.execute(f"CREATE OR REPLACE VIEW mt5.xauusd_bars_m1 AS SELECT * FROM read_parquet('{pattern}', hive_partitioning=true, union_by_name=true)")
        else:
            con.execute("CREATE OR REPLACE TABLE mt5.xauusd_bars_m1_empty(symbol VARCHAR, time BIGINT, open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE)")
        con.execute(
            "CREATE TABLE IF NOT EXISTS mt5.pipeline_runs(run_at_utc TIMESTAMP, action VARCHAR, details VARCHAR)"
        )
        con.execute("INSERT INTO mt5.pipeline_runs VALUES (?, ?, ?)", [datetime.now(timezone.utc), "duckdb-init", str(normalized_root)])
    finally:
        con.close()
    print(f"duckdb-init db={db_path}")


def duckdb_summary(args: Any) -> None:
    duckdb = _require_duckdb()
    db_path = _root(args.db)
    normalized_root = _root(args.normalized_root)
    date = args.date
    tick_pattern = normalized_root / "xauusd" / "ticks" / f"date={date}" / "*.parquet"
    bar_pattern = normalized_root / "xauusd" / "bars" / "timeframe=M1" / f"date={date}" / "*.parquet"
    con = duckdb.connect(str(db_path))
    try:
        tick_count = con.execute(f"SELECT count(*) FROM read_parquet('{tick_pattern}', union_by_name=true)").fetchone()[0] if list(tick_pattern.parent.glob("*.parquet")) else 0
        bar_count = con.execute(f"SELECT count(*) FROM read_parquet('{bar_pattern}', union_by_name=true)").fetchone()[0] if list(bar_pattern.parent.glob("*.parquet")) else 0
        print(f"date={date} tick_rows={tick_count} bar_rows={bar_count}")
        if tick_count:
            rows = con.execute(
                f"""
                SELECT
                  CAST(floor(time_msc / 60000) * 60000 AS BIGINT) AS minute_epoch_ms,
                  count(*) AS ticks_per_min,
                  avg(spread) AS spread_mean,
                  max(spread) AS spread_max,
                  first(mid ORDER BY time_msc) AS mid_open,
                  max(mid) AS mid_high,
                  min(mid) AS mid_low,
                  last(mid ORDER BY time_msc) AS mid_close,
                  last(mid ORDER BY time_msc) - first(mid ORDER BY time_msc) AS mid_return
                FROM read_parquet('{tick_pattern}', union_by_name=true)
                GROUP BY 1
                ORDER BY 1 DESC
                LIMIT 5
                """
            ).fetchall()
            print("latest minute summary:")
            for row in rows:
                print(row)
    finally:
        con.close()
