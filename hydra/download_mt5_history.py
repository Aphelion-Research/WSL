"""Download XAU/USD history from MT5 via Wine Python bridge.

This script calls Wine Python (which has MetaTrader5 module) to fetch
historical bars for all required timeframes and saves to parquet.
"""
import subprocess
import json
import sys
import os
from pathlib import Path
from datetime import datetime

WINEPREFIX = os.environ.get("DOMDATA_WINEPREFIX", os.path.expanduser("~/.mt5"))
WINE_PYTHON = "C:\\Python311\\python.exe"
OUTPUT_DIR = Path.home() / "Dominion" / "data" / "mt5_history"

TIMEFRAMES = ["M1", "M5", "M15", "H1", "H4", "D1"]
SYMBOL = "XAUUSD"

# Wine Python script that runs inside Wine/MT5 context
FETCH_SCRIPT = '''
import MetaTrader5 as mt5
import json
import sys
from datetime import datetime, timezone

symbol = sys.argv[1]
tf_name = sys.argv[2]
output_path = sys.argv[3]

TF_MAP = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
}

if not mt5.initialize():
    print(json.dumps({"error": f"MT5 init failed: {mt5.last_error()}"}))
    sys.exit(1)

tf = TF_MAP[tf_name]
rates = mt5.copy_rates_range(
    symbol, tf,
    datetime(2010, 1, 1, tzinfo=timezone.utc),
    datetime.now(timezone.utc)
)

mt5.shutdown()

if rates is None or len(rates) == 0:
    print(json.dumps({"error": "no data", "tf": tf_name}))
    sys.exit(1)

# Convert to list of dicts
rows = []
for r in rates:
    rows.append({
        "time": int(r["time"]),
        "open": float(r["open"]),
        "high": float(r["high"]),
        "low": float(r["low"]),
        "close": float(r["close"]),
        "tick_volume": int(r["tick_volume"]),
        "spread": int(r["spread"]),
        "real_volume": int(r["real_volume"]),
    })

with open(output_path, "w") as f:
    json.dump(rows, f)

print(json.dumps({
    "status": "ok",
    "tf": tf_name,
    "rows": len(rows),
    "first": rows[0]["time"],
    "last": rows[-1]["time"],
}))
'''


def fetch_timeframe(tf: str) -> dict:
    """Fetch one timeframe via Wine Python subprocess."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{SYMBOL}_{tf}_raw.json"

    # Write temp script
    script_path = OUTPUT_DIR / "_fetch_temp.py"
    script_path.write_text(FETCH_SCRIPT)

    # Convert paths for Wine
    wine_output = subprocess.run(
        ["winepath", "-w", str(output_path)],
        capture_output=True, text=True,
        env={**os.environ, "WINEPREFIX": WINEPREFIX}
    ).stdout.strip()

    wine_script = subprocess.run(
        ["winepath", "-w", str(script_path)],
        capture_output=True, text=True,
        env={**os.environ, "WINEPREFIX": WINEPREFIX}
    ).stdout.strip()

    # Run via Wine Python
    result = subprocess.run(
        ["wine", WINE_PYTHON, wine_script, SYMBOL, tf, wine_output],
        capture_output=True, text=True, timeout=120,
        env={**os.environ, "WINEPREFIX": WINEPREFIX}
    )

    if result.returncode != 0:
        return {"error": result.stderr[:500], "tf": tf}

    # Parse result
    for line in result.stdout.strip().split("\n"):
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue

    return {"error": "no valid JSON output", "tf": tf}


def convert_to_parquet(tf: str) -> dict:
    """Convert downloaded JSON to parquet."""
    import pandas as pd

    json_path = OUTPUT_DIR / f"{SYMBOL}_{tf}_raw.json"
    if not json_path.exists():
        return {"error": "json not found", "tf": tf}

    with open(json_path) as f:
        rows = json.load(f)

    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df = df.sort_values("timestamp").reset_index(drop=True)

    parquet_path = OUTPUT_DIR / f"{SYMBOL}_{tf}.parquet"
    df.to_parquet(parquet_path, index=False)

    first_date = df["timestamp"].iloc[0]
    last_date = df["timestamp"].iloc[-1]
    years = (last_date - first_date).days / 365.25

    return {
        "tf": tf,
        "rows": len(df),
        "first": str(first_date.date()),
        "last": str(last_date.date()),
        "years": round(years, 1),
        "parquet": str(parquet_path),
    }


def main():
    print("=" * 60)
    print("  MT5 HISTORY DOWNLOADER — XAU/USD ALL TIMEFRAMES")
    print("=" * 60)
    print()

    source_env = Path.home() / "Dominion" / "secrets" / "mt5.env"
    if source_env.exists():
        import subprocess as sp
        # Source env vars
        for line in source_env.read_text().splitlines():
            line = line.strip()
            if line.startswith("export "):
                line = line[7:]
            if "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                val = val.strip('"').strip("'")
                val = val.replace("$HOME", os.path.expanduser("~"))
                os.environ[key] = val

    results = {}
    for tf in TIMEFRAMES:
        print(f"  Fetching {tf}...", end=" ", flush=True)
        r = fetch_timeframe(tf)
        if "error" in r:
            print(f"FAILED: {r['error'][:100]}")
        else:
            print(f"OK: {r.get('rows', 0):,} bars")
            # Convert to parquet
            pr = convert_to_parquet(tf)
            results[tf] = pr
            print(f"    → {pr.get('first', '?')} to {pr.get('last', '?')} ({pr.get('years', 0)} years)")

    print()
    print("=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    for tf, info in results.items():
        print(f"  {tf:4s}: {info.get('rows', 0):>10,} bars | "
              f"{info.get('first', '?')} → {info.get('last', '?')} | "
              f"{info.get('years', 0)} years")

    # Save inventory
    inventory_path = OUTPUT_DIR / "inventory.json"
    with open(inventory_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  Inventory: {inventory_path}")

    # Check 9-year requirement
    if "D1" in results:
        years_d1 = results["D1"].get("years", 0)
        if years_d1 >= 9:
            print(f"\n  ✓ D1 has {years_d1} years — sufficient for 9-year experiment")
        else:
            print(f"\n  ✗ D1 has {years_d1} years — need 9 minimum")

    if "H1" in results:
        years_h1 = results["H1"].get("years", 0)
        print(f"  H1: {years_h1} years available")


if __name__ == "__main__":
    main()
