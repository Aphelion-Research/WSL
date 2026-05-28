#!/usr/bin/env python3
"""
HYDRA Rich Runner - Live dashboard for C++ training runs.
"""
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from threading import Thread
from typing import Dict, List, Optional

try:
    from rich.console import Console
    from rich.live import Live
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.layout import Layout
    from rich.text import Text
except ImportError:
    print("ERROR: Rich not installed. Run: bash scripts/install_rich_tools.sh")
    sys.exit(1)


PRESETS = {
    "direction-audit": {
        "data_dir": "data/hydra_binary_288b",
        "threads": 8,
        "horizon": 288,
        "split_mode": "train-oos",
        "train_years": 10,
        "oos_years": 1,
        "starting_balance": 10000,
        "leverage": 50,
        "max_loss_pct": 0.06,
        "lot_size": 0.01,
        "max_open_positions": 1,
        "max_holding_bars": 288,
        "min_long_confidence": 0.02,
        "min_short_confidence": 0.02,
        "min_rr": 1.0,
        "max_rr": 3.0,
        "risk_per_trade_pct": 0.0001,
        "trail_activate_r": 1.0,
        "trail_distance_r": 0.5,
        "move_sl_to_breakeven_at_r": 1.0,
        "max_saturation_rate": 0.95,
        "min_proba_std": 0.001,
        "min_confidence": 0.02,
        "flags": [
            "--hard-stop-on-drawdown",
            "--require-bracket-orders",
            "--allow-long",
            "--allow-short",
            "--confidence-rr",
            "--trailing-stop",
            "--normalize-features",
            "--calibrate-proba",
            "--regime-filter",
            "--reject-constant-proba",
            "--disable-rank-ensemble",
            "--objective", "excess_utility",
        ],
    },
}


class HydraState:
    def __init__(self):
        self.start_time = time.time()
        self.rows = 0
        self.cols = 0
        self.threads = 0
        self.split_mode = ""
        self.openmp_enabled = False
        self.self_tests: List[Dict] = []
        self.current_config = ""
        self.current_stage = ""
        self.config_index = 0
        self.config_total = 0
        self.results: List[Dict] = []
        self.warnings: List[str] = []
        self.done = False
        self.elapsed_seconds = 0

    def elapsed(self) -> int:
        if self.done:
            return self.elapsed_seconds
        return int(time.time() - self.start_time)


def build_command(preset: str, extra_args: List[str]) -> tuple[List[str], str]:
    """Build HYDRA command from preset + extra args."""
    if preset not in PRESETS:
        raise ValueError(f"Unknown preset: {preset}")

    config = PRESETS[preset]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    progress_path = f"reports/hydra_progress_{preset}_{timestamp}.jsonl"

    cmd = ["./build/hydra_288b_fast_train"]

    for key, value in config.items():
        if key == "flags":
            cmd.extend(value)
        else:
            flag_name = key.replace("_", "-")
            cmd.append(f"--{flag_name}")
            cmd.append(str(value))

    cmd.append("--progress-jsonl")
    cmd.append(progress_path)

    if extra_args:
        cmd.extend(extra_args)

    return cmd, progress_path


def render_dashboard(state: HydraState) -> Layout:
    """Render Rich dashboard layout."""
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=6),
        Layout(name="body"),
        Layout(name="footer", size=8),
    )

    # Header
    header_text = Text()
    header_text.append("HYDRA C++ TRAINING CONTROL ROOM\n", style="bold cyan")
    header_text.append(f"Elapsed: {state.elapsed()}s | ", style="white")
    header_text.append(f"Threads: {state.threads} | ", style="green")
    header_text.append(f"OpenMP: {'yes' if state.openmp_enabled else 'no'} | ", style="green" if state.openmp_enabled else "yellow")
    header_text.append(f"Mode: {state.split_mode}\n", style="blue")
    header_text.append(f"Config: [{state.config_index}/{state.config_total}] {state.current_config}", style="magenta")
    layout["header"].update(Panel(header_text, title="Status", border_style="cyan"))

    # Body: Results table
    table = Table(title="Results", show_header=True, header_style="bold magenta")
    table.add_column("Config", style="cyan", width=30)
    table.add_column("Return %", justify="right", style="green")
    table.add_column("Baseline %", justify="right", style="yellow")
    table.add_column("Excess %", justify="right", style="blue")
    table.add_column("Trades", justify="right")
    table.add_column("Win %", justify="right")
    table.add_column("PF", justify="right")
    table.add_column("MaxDD %", justify="right")
    table.add_column("Signal", style="white")
    table.add_column("Risk", style="white")
    table.add_column("Edge", style="white")

    for res in state.results[-20:]:  # Show last 20
        signal_color = "green" if res.get("signal_verdict") == "PASS_SIGNAL_SANITY" else "red"
        risk_color = "green" if res.get("risk_verdict") == "PASS_RISK" else "red"
        edge_color = "green" if res.get("model_edge_verdict") == "EDGE_CONFIRMED" else (
            "yellow" if res.get("model_edge_verdict") in ["BASELINE_DOMINATED", "NO_TRADE"] else "red"
        )

        table.add_row(
            res.get("config", ""),
            f"{res.get('return_pct', 0) * 100:.2f}",
            f"{res.get('best_baseline_return_pct', 0) * 100:.2f}",
            f"{res.get('model_excess_return_pct', 0) * 100:.2f}",
            str(res.get("total_trades", 0)),
            f"{res.get('win_rate', 0) * 100:.1f}",
            f"{res.get('profit_factor', 0):.2f}",
            f"{res.get('max_drawdown_pct', 0) * 100:.1f}",
            Text(res.get("signal_verdict", ""), style=signal_color),
            Text(res.get("risk_verdict", ""), style=risk_color),
            Text(res.get("model_edge_verdict", ""), style=edge_color),
        )

    layout["body"].update(table)

    # Footer: Warnings
    warning_text = Text()
    for w in state.warnings[-10:]:  # Show last 10
        warning_text.append(f"• {w}\n", style="yellow")
    layout["footer"].update(Panel(warning_text, title="Warnings", border_style="yellow"))

    return layout


def tail_progress(progress_path: str, state: HydraState):
    """Tail progress JSONL and update state."""
    Path(progress_path).parent.mkdir(parents=True, exist_ok=True)
    Path(progress_path).touch()

    with open(progress_path, "r") as f:
        while not state.done:
            line = f.readline()
            if not line:
                time.sleep(0.1)
                continue

            try:
                event = json.loads(line)
                handle_event(event, state)
            except json.JSONDecodeError:
                pass


def handle_event(event: Dict, state: HydraState):
    """Handle progress event."""
    etype = event.get("event")

    if etype == "run_start":
        state.threads = event.get("threads", 0)
        state.split_mode = event.get("split_mode", "")
        state.openmp_enabled = event.get("openmp_enabled", False)

    elif etype == "data_loaded":
        state.rows = event.get("rows", 0)
        state.cols = event.get("cols", 0)

    elif etype == "self_test":
        state.self_tests.append(event)

    elif etype == "config_start":
        state.current_config = event.get("config", "")
        state.config_index = event.get("config_index", 0)
        state.config_total = event.get("config_total", 0)

    elif etype == "signal_sanity":
        if event.get("signal_verdict") != "PASS_SIGNAL_SANITY":
            state.warnings.append(f"{event.get('config')}: {event.get('signal_verdict')}")

    elif etype == "broker_result":
        pass  # Will be aggregated in config_done

    elif etype == "baseline_eval":
        pass

    elif etype == "config_done":
        result = {
            "config": event.get("config"),
            "risk_verdict": event.get("risk_verdict"),
            "signal_verdict": event.get("signal_verdict"),
            "model_edge_verdict": event.get("model_edge_verdict"),
            "return_pct": event.get("return_pct", 0),
            "model_excess_return_pct": event.get("model_excess_return_pct", 0),
            "total_trades": event.get("total_trades", 0),
            "win_rate": 0,  # Not in config_done yet
            "profit_factor": 0,
            "max_drawdown_pct": 0,
            "best_baseline_return_pct": 0,
        }
        state.results.append(result)

        if event.get("model_edge_verdict") not in ["EDGE_CONFIRMED", "NO_TRADE"]:
            state.warnings.append(f"{event.get('config')}: {event.get('model_edge_verdict')}")

    elif etype == "run_done":
        state.done = True
        state.elapsed_seconds = event.get("elapsed_seconds", 0)


def run_hydra(cmd: List[str], progress_path: str, log_path: str):
    """Run HYDRA subprocess and capture logs."""
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)

    with open(log_path, "w") as log_file:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        for line in process.stdout:
            log_file.write(line)
            log_file.flush()

        process.wait()
        return process.returncode


def main():
    parser = argparse.ArgumentParser(description="HYDRA Rich Runner")
    parser.add_argument("--preset", required=True, choices=PRESETS.keys(), help="Preset config")
    parser.add_argument("--extra-arg", action="append", default=[], help="Extra CLI args")
    args = parser.parse_args()

    console = Console()

    # Check binary
    if not Path("build/hydra_288b_fast_train").exists():
        console.print("[red]Binary missing. Run: bash scripts/build_hydra_cpp.sh[/red]")
        sys.exit(1)

    # Build command
    cmd, progress_path = build_command(args.preset, args.extra_arg)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = f"reports/hydra_rich_{args.preset}_{timestamp}.log"

    console.print(f"[cyan]Starting HYDRA: {args.preset}[/cyan]")
    console.print(f"[cyan]Progress: {progress_path}[/cyan]")
    console.print(f"[cyan]Log: {log_path}[/cyan]")

    state = HydraState()

    # Start progress tail thread
    tail_thread = Thread(target=tail_progress, args=(progress_path, state), daemon=True)
    tail_thread.start()

    # Start HYDRA subprocess
    run_thread = Thread(target=run_hydra, args=(cmd, progress_path, log_path), daemon=False)
    run_thread.start()

    # Live dashboard
    with Live(render_dashboard(state), refresh_per_second=2, console=console) as live:
        while not state.done and run_thread.is_alive():
            live.update(render_dashboard(state))
            time.sleep(0.5)

        # Final update
        live.update(render_dashboard(state))

    run_thread.join()

    console.print(f"\n[green]HYDRA run completed in {state.elapsed()}s[/green]")
    console.print(f"[cyan]Results: runs/hydra_cpp_288b_results.csv[/cyan]")
    console.print(f"[cyan]Log: {log_path}[/cyan]")


if __name__ == "__main__":
    main()
