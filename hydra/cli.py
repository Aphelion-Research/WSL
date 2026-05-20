"""CLI entry points for `dominion hydra ...` commands."""
from __future__ import annotations

import argparse
import sys
import json


def cmd_train(args):
    """dominion hydra train"""
    from hydra.loop.improver import HydraImprover
    improver = HydraImprover(brain=args.brain, no_loop=args.no_loop)
    result = improver.run()
    print(json.dumps(result, indent=2, default=str))


def cmd_predict(args):
    """dominion hydra predict"""
    print(json.dumps({"status": "predict", "brain": args.brain, "date": args.date}))


def cmd_report(args):
    """dominion hydra report"""
    from hydra.storage.duckdb_writer import HydraDB
    db = HydraDB()
    import duckdb
    con = duckdb.connect(str(db.db_path), read_only=True)
    rows = con.execute(
        f"SELECT * FROM hydra_iterations ORDER BY iter DESC LIMIT {args.last_n}"
    ).fetchall()
    con.close()
    for row in rows:
        print(row)


def cmd_backtest(args):
    """dominion hydra backtest"""
    print(json.dumps({"status": "backtest", "from": args.from_date, "to": args.to_date}))


def cmd_export(args):
    """dominion hydra export"""
    print(json.dumps({"status": "export", "out": args.out}))


def cmd_cpp_build(args):
    """dominion hydra cpp-build"""
    import subprocess
    build_dir = "hydra/backtest/cpp/build"
    subprocess.run(["cmake", "-B", build_dir, "hydra/backtest/cpp/"], check=True)
    subprocess.run(["cmake", "--build", build_dir, "-j"], check=True)
    print("C++ backtester built successfully")


def cmd_cpp_run(args):
    """dominion hydra cpp-run"""
    print(json.dumps({"status": "cpp_run", "fold": args.fold}))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dominion hydra")
    sub = parser.add_subparsers(dest="command")

    p_train = sub.add_parser("train")
    p_train.add_argument("--brain", default="all", choices=["scalp", "day", "swing", "all"])
    p_train.add_argument("--no-loop", action="store_true")
    p_train.set_defaults(func=cmd_train)

    p_predict = sub.add_parser("predict")
    p_predict.add_argument("--brain", default="all")
    p_predict.add_argument("--date", default=None)
    p_predict.set_defaults(func=cmd_predict)

    p_report = sub.add_parser("report")
    p_report.add_argument("--last-n", type=int, default=50)
    p_report.set_defaults(func=cmd_report)

    p_bt = sub.add_parser("backtest")
    p_bt.add_argument("--from", dest="from_date", default=None)
    p_bt.add_argument("--to", dest="to_date", default=None)
    p_bt.set_defaults(func=cmd_backtest)

    p_export = sub.add_parser("export")
    p_export.add_argument("--out", default="artifacts/hydra/hydra_fused.int4.onnx")
    p_export.set_defaults(func=cmd_export)

    p_cpp_build = sub.add_parser("cpp-build")
    p_cpp_build.set_defaults(func=cmd_cpp_build)

    p_cpp_run = sub.add_parser("cpp-run")
    p_cpp_run.add_argument("--fold", type=int, default=0)
    p_cpp_run.set_defaults(func=cmd_cpp_run)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
