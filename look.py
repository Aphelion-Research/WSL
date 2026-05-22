#!/usr/bin/env python3
"""
Live training monitor - shows real-time progress from actual results (no estimates).
"""
import subprocess
import time
import os
import sys
from datetime import datetime
from pathlib import Path

TRAINING_PID = 12488
EXPECTED_CONFIGS = 10
EXPECTED_FOLDS = 5
EXPECTED_TOTAL_RUNS = EXPECTED_CONFIGS * EXPECTED_FOLDS

CSV_FILE = Path("runs/hydra_fixed_commission_288b_10runs.csv")
LOG_FILE = Path("reports/hydra_train_fixed_commission_288b_log.txt")

def get_process_info():
    """Get process stats."""
    try:
        result = subprocess.run(['ps', '-p', str(TRAINING_PID)],
                              capture_output=True, text=True)
        if result.returncode != 0:
            return None

        result = subprocess.run(
            ['ps', '-p', str(TRAINING_PID), '-o', 'etime=,pcpu=,rss=,stat='],
            capture_output=True, text=True
        )

        if result.returncode == 0:
            parts = result.stdout.strip().split()
            if len(parts) >= 4:
                return {
                    'runtime': parts[0],
                    'cpu': float(parts[1]),
                    'ram_mb': int(parts[2]) / 1024,
                    'status': parts[3]
                }
    except:
        pass
    return None

def parse_runtime(runtime_str):
    """Parse runtime string to seconds."""
    parts = runtime_str.split(':')
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    else:
        return 0

def get_real_progress():
    """Get ACTUAL progress from CSV file (no estimates)."""
    if not CSV_FILE.exists():
        return None

    try:
        with open(CSV_FILE, 'r') as f:
            lines = [line for line in f if line.strip()]
            if len(lines) <= 1:  # Only header
                return None
            return max(0, len(lines) - 1)  # -1 for header
    except:
        return None

def get_log_tail(n=20):
    """Get last N lines of log."""
    if LOG_FILE.exists() and LOG_FILE.stat().st_size > 0:
        try:
            with open(LOG_FILE, 'r') as f:
                lines = f.readlines()
                return lines[-n:] if lines else []
        except:
            pass
    return []

def format_eta(seconds):
    """Format ETA."""
    if seconds <= 0:
        return "calculating..."

    mins = int(seconds / 60)
    secs = int(seconds % 60)

    if mins > 60:
        hours = mins // 60
        mins = mins % 60
        return f"{hours}h {mins}m"
    elif mins > 0:
        return f"{mins}m {secs}s"
    else:
        return f"{secs}s"

def monitor():
    """Monitor training with REAL data only (no estimates)."""
    print("=" * 80)
    print("HYDRA TRAINING MONITOR - REAL DATA ONLY")
    print("=" * 80)
    print(f"PID: {TRAINING_PID}")
    print(f"Expected: {EXPECTED_TOTAL_RUNS} runs ({EXPECTED_CONFIGS} configs × {EXPECTED_FOLDS} folds)")
    print(f"CSV file: {CSV_FILE}")
    print()
    print("Waiting for real results (no estimates shown)...")
    print("=" * 80)
    print()

    last_completed = 0
    first_result_time = None

    try:
        while True:
            os.system('clear' if os.name == 'posix' else 'cls')

            print("=" * 80)
            print(f"HYDRA TRAINING MONITOR - {datetime.now().strftime('%H:%M:%S')}")
            print("=" * 80)

            # Process info
            proc_info = get_process_info()

            if proc_info is None:
                print("\n✓ TRAINING COMPLETE (process ended)")
                print("\nChecking results...")

                if CSV_FILE.exists():
                    print(f"✓ Results saved: {CSV_FILE}")
                    with open(CSV_FILE, 'r') as f:
                        rows = sum(1 for _ in f) - 1
                        print(f"  Total runs: {rows}")

                print(f"\nView log: cat {LOG_FILE}")
                break

            print(f"\nPROCESS STATUS:")
            print(f"  Runtime:  {proc_info['runtime']}")
            print(f"  CPU:      {proc_info['cpu']:.1f}%")
            print(f"  RAM:      {proc_info['ram_mb']:.1f} MB ({proc_info['ram_mb']/1024:.1f} GB)")
            print(f"  Status:   {proc_info['status']} (R=Running)")

            # Real progress from CSV
            completed = get_real_progress()

            if completed is None:
                print(f"\nPROGRESS:")
                print(f"  Waiting for first config to complete...")
                print(f"  CSV file: {CSV_FILE}")
                print(f"  Status: {'exists (empty)' if CSV_FILE.exists() else 'not created yet'}")
                print(f"\n  Training is active - computing first config")
                print(f"  Progress will show when CSV file contains results")
            else:
                # Real data available
                progress_pct = (completed / EXPECTED_TOTAL_RUNS * 100) if EXPECTED_TOTAL_RUNS > 0 else 0

                print(f"\nPROGRESS (REAL DATA):")
                print(f"  Completed: {completed}/{EXPECTED_TOTAL_RUNS} runs ({progress_pct:.1f}%)")

                # Progress bar
                bar_width = 50
                filled = int(bar_width * progress_pct / 100)
                bar = '█' * filled + '░' * (bar_width - filled)
                print(f"  [{bar}] {progress_pct:.1f}%")

                # ETA based on actual rate
                if completed > last_completed:
                    runtime_sec = parse_runtime(proc_info['runtime'])
                    if first_result_time is None:
                        first_result_time = runtime_sec

                    # Rate from when first result appeared
                    time_since_first = runtime_sec - (first_result_time if first_result_time else 0)
                    rate_per_run = time_since_first / completed if completed > 0 else 0
                    remaining = (EXPECTED_TOTAL_RUNS - completed) * rate_per_run

                    print(f"  ETA:       {format_eta(remaining)} (based on actual {rate_per_run:.0f}s per run)")
                    last_completed = completed
                elif completed > 0:
                    runtime_sec = parse_runtime(proc_info['runtime'])
                    rate_per_run = runtime_sec / completed if completed > 0 else 0
                    remaining = (EXPECTED_TOTAL_RUNS - completed) * rate_per_run
                    print(f"  ETA:       {format_eta(remaining)} (est. {rate_per_run:.0f}s per run)")

            # Recent log activity
            print(f"\nRECENT LOG (last 15 lines):")
            log_lines = get_log_tail(15)

            if log_lines:
                for line in log_lines:
                    line = line.strip()
                    if line:
                        if 'CONFIG' in line or 'Fold' in line:
                            print(f"  >> {line}")
                        elif 'AUC' in line or 'Sharpe' in line or 'Net' in line:
                            print(f"  → {line}")
                        elif 'VERDICT' in line:
                            print(f"  ★ {line}")
                        else:
                            print(f"     {line}")
            else:
                print("  (Python output buffered - logs will flush when training completes)")

            # Files status
            print(f"\nOUTPUT FILES:")
            csv_status = 'exists' if CSV_FILE.exists() else 'not created'
            log_size = LOG_FILE.stat().st_size if LOG_FILE.exists() else 0
            print(f"  CSV:  {csv_status} - {CSV_FILE}")
            print(f"  Log:  {log_size} bytes (buffered) - {LOG_FILE}")

            print("\n" + "=" * 80)
            print("Press Ctrl+C to stop monitoring (training continues)")
            print("Refreshing every 2 seconds...")

            time.sleep(2)

    except KeyboardInterrupt:
        print("\n\nMonitor stopped. Training continues in background.")
        print(f"Check status: ps -p {TRAINING_PID}")
        print(f"Check results: cat {CSV_FILE}")

if __name__ == "__main__":
    proc_info = get_process_info()
    if proc_info is None:
        print(f"✗ Training process {TRAINING_PID} not found")
        print("Training may have finished.")
        if CSV_FILE.exists():
            print(f"\n✓ Results: {CSV_FILE}")
        sys.exit(1)

    monitor()
