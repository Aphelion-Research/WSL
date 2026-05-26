#!/usr/bin/env python3
"""
C++ Dataset Builder Frontend
Launches the fast parallel C++ builder with real-time progress bar.
"""

import sys
import os
import time
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "dominion_cpp" / "build"))

try:
    import dominion_features as cpp_lib
except ImportError:
    print("ERROR: dominion_features C++ module not found. Run:")
    print("  cd dominion_cpp/build && cmake .. && make -j")
    sys.exit(1)

def progress_monitor(progress_state):
    """Monitor and display progress bar."""
    try:
        while progress_state.building:
            sys.stdout.write('\r' + progress_state.format_progress())
            sys.stdout.flush()
            time.sleep(0.1)
        sys.stdout.write('\n')
        sys.stdout.flush()
    except KeyboardInterrupt:
        print("\n\nBuild interrupted by user")
        sys.exit(1)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Fast C++ dataset builder")
    parser.add_argument("--input", default=str(ROOT / "data" / "mt5_history" / "XAUUSD_M5_MASTER.parquet"))
    parser.add_argument("--output", default=str(ROOT / "data" / "feature_fabric" / "hydra_cpp_v2.parquet"))
    parser.add_argument("--rows", type=int, default=0, help="Limit rows (0=all)")
    parser.add_argument("--threads", type=int, default=-1, help="Threads (-1=auto)")
    parser.add_argument("--skip-validation", action="store_true")
    args = parser.parse_args()

    print("=" * 60)
    print("HYDRA C++ Dataset Builder v2")
    print("=" * 60)
    print(f"Input: {args.input}")
    print(f"Output: {args.output}")
    print(f"Threads: {args.threads if args.threads > 0 else 'auto'}")
    print()

    # Create builder config
    config = cpp_lib.DatasetConfig()
    config.input_path = args.input
    config.output_path = args.output
    config.max_rows = args.rows
    config.num_threads = args.threads
    config.skip_validation = args.skip_validation

    # Initialize C++ builder
    print("[C++] Initializing builder...")
    try:
        builder = cpp_lib.DatasetBuilderV2(config)
    except AttributeError:
        print("ERROR: DatasetBuilderV2 not found in C++ module")
        print("The C++ implementation is not yet compiled into the module.")
        print()
        print("For now, use the Python builder:")
        print("  python scripts/build_hydra_feature_fabric.py")
        sys.exit(1)

    # Start progress monitor in background
    progress_state = builder.get_progress()
    monitor_thread = threading.Thread(target=progress_monitor, args=(progress_state,), daemon=True)
    monitor_thread.start()

    # Build
    start = time.time()
    success = builder.build()
    elapsed = time.time() - start

    if success:
        print()
        print("=" * 60)
        print("BUILD COMPLETE")
        print(f"Time: {elapsed:.1f}s")
        print(f"Output: {args.output}")
        print("=" * 60)
    else:
        print()
        print("BUILD FAILED")
        sys.exit(1)

if __name__ == "__main__":
    main()
