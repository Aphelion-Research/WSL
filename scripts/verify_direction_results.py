#!/usr/bin/env python3
import csv
from pathlib import Path
from collections import Counter

def exists_size(p):
    path = Path(p)
    return path.exists(), path.stat().st_size if path.exists() else 0

def first_nonempty(row, *keys, default=""):
    for k in keys:
        v = row.get(k)
        if v is not None and str(v).strip() != "":
            return v
    return default

def fnum(v, default=0.0):
    try:
        if v is None or str(v).strip() == "":
            return default
        return float(v)
    except Exception:
        return default

print("=== MODEL FILES ===")
for p in [
    "runs/models/hydra_long.bin",
    "runs/models/hydra_short.bin",
    "runs/hydra_dual_specialist_results.csv",
    "runs/hydra_cpp_288b_results.csv",
    "runs/hydra_cpp_288b_trades.csv",
]:
    ok, size = exists_size(p)
    print(f"{p}: exists={ok} size={size}")

print("\n=== RESULTS ===")
# Prefer dual specialist dedicated CSV
if Path("runs/hydra_dual_specialist_results.csv").exists():
    results_path = Path("runs/hydra_dual_specialist_results.csv")
    print("Using: runs/hydra_dual_specialist_results.csv")
elif Path("runs/hydra_cpp_288b_results.csv").exists():
    results_path = Path("runs/hydra_cpp_288b_results.csv")
    print("Using: runs/hydra_cpp_288b_results.csv")
else:
    raise SystemExit("Missing results CSV")

with results_path.open(newline="") as f:
    rows = list(csv.DictReader(f))

print("rows:", len(rows))

for r in rows:
    config = first_nonempty(r, "config", default="<missing>")
    direction = first_nonempty(r, "direction_mode", default="")
    ret = fnum(first_nonempty(r, "return_pct", "combined_return_pct"))
    excess = fnum(first_nonempty(r, "combined_excess_pct", "model_excess_return_pct"))
    edge = first_nonempty(r, "model_edge_verdict", default="")
    risk = first_nonempty(r, "risk_verdict", default="")
    long_trades = first_nonempty(r, "long_trades", default="0")
    short_trades = first_nonempty(r, "short_trades", default="0")
    hedge = first_nonempty(r, "hedge_violations", default="0")
    best_base = first_nonempty(r, "best_baseline_name_dual", "best_baseline_name", default="")
    best_base_ret = fnum(first_nonempty(r, "best_baseline_return_pct_dual", "best_baseline_return_pct"))

    print(
        f"{config[:32]:32} | mode={direction[:16]:16} | "
        f"ret={ret*100:8.2f}% | base={best_base[:14]:14} {best_base_ret*100:8.2f}% | "
        f"excess={excess*100:8.2f}% | edge={edge[:20]:20} | risk={risk[:12]:12} | "
        f"L={long_trades:>6} S={short_trades:>6} | hedge={hedge}"
    )

print("\n=== TRADES ===")
trades_path = Path("runs/hydra_cpp_288b_trades.csv")
if trades_path.exists():
    dirs = Counter()
    exits = Counter()
    n = 0
    with trades_path.open(newline="") as f:
        reader = csv.DictReader(f)
        print("columns:", reader.fieldnames[:25] if reader.fieldnames else None)
        for row in reader:
            n += 1
            dirs[row.get("direction")] += 1
            exits[row.get("exit_reason")] += 1

    print("trade_rows:", n)
    print("directions:", dict(dirs))
    print("exits:", dict(exits))

    if None in dirs:
        raise SystemExit("CSV parse failed: direction column missing/misaligned")
else:
    print("No trades CSV found.")
