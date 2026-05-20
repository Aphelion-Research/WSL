"""HYDRA Progress Dashboard — always-on war room terminal UI.

Usage:
    python -m hydra.progress              # one-shot render
    python -m hydra.progress --watch      # live refresh
    python -m hydra.progress --watch --refresh 0.5
    python -m hydra.progress --json       # raw JSON state
    python -m hydra.progress --logs --tail 100
    python -m hydra.progress --last-run
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

STATE_PATH = Path.home() / "Dominion" / "runs" / "hydra_runtime_state.json"
RUNS_DIR = Path.home() / "Dominion" / "runs"


def load_state() -> dict:
    try:
        with open(STATE_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "schema_version": 1, "active": False, "status": "IDLE",
            "phase": "IDLE", "mode": "none", "current_task": "No training at this time",
            "progress_pct": 0, "phase_progress_pct": 0, "run_id": None,
            "symbol": "XAUUSD", "timeframe": "none", "provider": "Unknown",
            "iteration": 0, "max_iterations": 0, "rows_done": 0, "rows_total": 0,
            "bars_done": 0, "bars_total": 0, "files_done": 0, "files_total": 0,
            "started_at": None, "updated_at": None, "eta_seconds": None,
            "eta_human": "N/A", "latest_log_file": None, "last_error": None,
            "warnings": [], "metrics_preview": {}, "modes": {}, "providers": {},
            "system": {},
        }


def find_latest_log(state: dict) -> Path | None:
    if state.get("latest_log_file"):
        p = Path(state["latest_log_file"])
        if p.exists():
            return p
    run_id = state.get("run_id")
    if run_id:
        log = RUNS_DIR / run_id / "logs" / "run.log"
        if log.exists():
            return log
    # Find most recent run dir
    candidates = sorted(RUNS_DIR.glob("hydra_*/logs/run.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def tail_file(path: Path, n: int = 50) -> list[str]:
    try:
        lines = path.read_text().splitlines()
        return lines[-n:]
    except (FileNotFoundError, OSError):
        return []


def find_latest_events(state: dict) -> list[dict]:
    run_id = state.get("run_id")
    events_path = None
    if run_id:
        events_path = RUNS_DIR / run_id / "events.jsonl"
    if not events_path or not events_path.exists():
        candidates = sorted(RUNS_DIR.glob("hydra_*/events.jsonl"),
                            key=lambda p: p.stat().st_mtime, reverse=True)
        events_path = candidates[0] if candidates else None
    if not events_path or not events_path.exists():
        return []
    try:
        lines = events_path.read_text().splitlines()[-10:]
        return [json.loads(l) for l in lines if l.strip()]
    except (json.JSONDecodeError, OSError):
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Rich dashboard
# ─────────────────────────────────────────────────────────────────────────────

def render_rich(state: dict) -> "rich.console.RenderableType":
    from rich.table import Table
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.text import Text
    from rich.progress_bar import ProgressBar
    from rich.columns import Columns
    from rich import box

    active = state.get("active", False)
    status = state.get("status", "IDLE")
    phase = state.get("phase", "IDLE")

    status_color = {"RUNNING": "green", "FAILED": "red", "COMPLETE": "cyan",
                    "IDLE": "yellow"}.get(status, "white")

    # Header panel
    header_lines = []
    header_lines.append(f"[bold {status_color}]Status      {status}[/]")
    header_lines.append(f"Phase       [bold]{phase}[/]")
    header_lines.append(f"Mode        {state.get('mode', 'none').upper()}")
    header_lines.append(f"Provider    {state.get('provider', 'Unknown')}")
    if state.get("run_id"):
        header_lines.append(f"Run ID      {state['run_id']}")
    header_lines.append(f"Task        {state.get('current_task', 'N/A')}")
    if active and state.get("eta_human"):
        header_lines.append(f"ETA         [bold]{state['eta_human']}[/]")
    header = Panel("\n".join(header_lines), title="[bold white]HYDRA CONTROL ROOM[/]",
                   border_style="bright_blue", box=box.DOUBLE)

    # Progress bars
    progress_lines = []
    overall_pct = state.get("progress_pct", 0) or 0
    phase_pct = state.get("phase_progress_pct", 0) or 0
    progress_lines.append(f"Overall     [{'█' * int(overall_pct / 3.125)}{'░' * (32 - int(overall_pct / 3.125))}] {overall_pct:5.1f}%")
    progress_lines.append(f"Phase       [{'█' * int(phase_pct / 3.125)}{'░' * (32 - int(phase_pct / 3.125))}] {phase_pct:5.1f}%")

    if state.get("iteration") and state.get("max_iterations"):
        it = state["iteration"]
        mx = state["max_iterations"]
        it_pct = (it / mx) * 100 if mx > 0 else 0
        progress_lines.append(f"Iterations  [{'█' * int(it_pct / 3.125)}{'░' * (32 - int(it_pct / 3.125))}] {it}/{mx}")

    progress_text = "\n".join(progress_lines)

    # Metrics
    mp = state.get("metrics_preview", {})
    metrics_lines = []
    if mp.get("best_validation_sharpe") is not None:
        metrics_lines.append(f"Best validation Sharpe: [bold green]{mp['best_validation_sharpe']:.3f}[/]")
    if mp.get("best_validation_profit_factor") is not None:
        metrics_lines.append(f"Best PF: {mp['best_validation_profit_factor']:.3f}")
    if mp.get("trades_so_far"):
        metrics_lines.append(f"Trades so far: {mp['trades_so_far']}")
    if mp.get("current_oos_locked"):
        metrics_lines.append("[dim]OOS: LOCKED UNTIL FINAL[/]")

    # System
    sys_info = state.get("system", {})
    sys_lines = []
    if sys_info.get("cpu_pct") is not None:
        sys_lines.append(f"CPU: {sys_info['cpu_pct']:.0f}%")
    if sys_info.get("ram_used_gb") is not None:
        sys_lines.append(f"RAM: {sys_info['ram_used_gb']} / {sys_info.get('ram_total_gb', '?')} GB")
    if sys_info.get("gpu_available"):
        sys_lines.append(f"GPU: {sys_info.get('gpu_name', '?')}, {sys_info.get('gpu_util_pct', 0):.0f}%, VRAM {sys_info.get('gpu_vram_used_gb', 0)} / {sys_info.get('gpu_vram_total_gb', 0)} GB")

    # Modes table
    modes = state.get("modes", {})
    mode_table = Table(title="Modes", box=box.SIMPLE, show_header=True)
    mode_table.add_column("Mode", style="bold")
    mode_table.add_column("Status")
    mode_table.add_column("Progress")
    mode_table.add_column("Sharpe")
    mode_table.add_column("Trades")
    for mname, minfo in modes.items():
        mstatus = minfo.get("status", "pending")
        color = {"complete": "green", "running": "cyan", "invalid": "red",
                 "failed": "red", "pending": "dim"}.get(mstatus, "white")
        sharpe = f"{minfo['best_validation_sharpe']:.3f}" if minfo.get("best_validation_sharpe") else "-"
        mode_table.add_row(
            mname.upper(),
            f"[{color}]{mstatus}[/]",
            f"{minfo.get('progress_pct', 0):.0f}%",
            sharpe,
            str(minfo.get("trades", 0)),
        )

    # Providers table
    providers = state.get("providers", {})
    prov_table = Table(title="Providers", box=box.SIMPLE, show_header=True)
    prov_table.add_column("Provider", style="bold")
    prov_table.add_column("Status")
    prov_table.add_column("Coverage")
    for pname, pinfo in providers.items():
        pstatus = pinfo.get("status", "unknown")
        color = {"valid": "green", "checking": "cyan", "insufficient": "yellow",
                 "failed": "red", "unknown": "dim"}.get(pstatus, "white")
        cov = f"{pinfo['coverage_pct']:.0f}%" if pinfo.get("coverage_pct") else "-"
        prov_table.add_row(pname, f"[{color}]{pstatus}[/]", cov)

    # Events
    events = find_latest_events(state)
    event_lines = []
    for ev in events[-8:]:
        ts_short = ev.get("ts", "")[-8:] if ev.get("ts") else ""
        lvl = ev.get("level", "INFO")
        color = {"ERROR": "red", "WARNING": "yellow", "SUCCESS": "green"}.get(lvl, "white")
        event_lines.append(f"[dim]{ts_short}[/] [{color}]{ev.get('message', '')}[/]")

    # Compose
    parts = [header, "", progress_text, ""]
    if metrics_lines:
        parts.append("\n".join(metrics_lines))
        parts.append("")
    if sys_lines:
        parts.append("  ".join(sys_lines))
        parts.append("")
    parts.append(mode_table)
    parts.append(prov_table)
    if event_lines:
        parts.append("\n[bold]Recent events:[/]")
        parts.append("\n".join(event_lines))

    if not active:
        parts.append("")
        parts.append("[dim]No active training. No active download. No active feature build.[/]")
        parts.append("")
        parts.append("[bold]Next suggested command:[/]")
        parts.append("python -m hydra.data_sources.registry --audit --symbol XAUUSD --years 9")

    if state.get("warnings"):
        parts.append("")
        parts.append("[bold yellow]Warnings:[/]")
        for w in state["warnings"][-5:]:
            parts.append(f"  [yellow]• {w}[/]")

    if state.get("last_error"):
        parts.append("")
        parts.append(f"[bold red]Last error: {state['last_error']}[/]")

    from rich.console import Group
    renderables = []
    for p in parts:
        if isinstance(p, str):
            renderables.append(Text.from_markup(p) if "[" in p else Text(p))
        else:
            renderables.append(p)
    return Group(*renderables)


# ─────────────────────────────────────────────────────────────────────────────
# Plain fallback
# ─────────────────────────────────────────────────────────────────────────────

def render_plain(state: dict) -> str:
    lines = []
    lines.append("=" * 60)
    lines.append("  HYDRA CONTROL ROOM")
    lines.append("=" * 60)
    lines.append(f"  Status:    {state.get('status', 'IDLE')}")
    lines.append(f"  Phase:     {state.get('phase', 'IDLE')}")
    lines.append(f"  Mode:      {state.get('mode', 'none')}")
    lines.append(f"  Provider:  {state.get('provider', 'Unknown')}")
    lines.append(f"  Task:      {state.get('current_task', 'N/A')}")
    lines.append(f"  Progress:  {state.get('progress_pct', 0):.1f}%")
    lines.append(f"  Phase:     {state.get('phase_progress_pct', 0):.1f}%")
    lines.append(f"  ETA:       {state.get('eta_human', 'N/A')}")
    if state.get("iteration"):
        lines.append(f"  Iteration: {state['iteration']}/{state.get('max_iterations', '?')}")
    lines.append("")
    mp = state.get("metrics_preview", {})
    if mp.get("best_validation_sharpe") is not None:
        lines.append(f"  Best Sharpe: {mp['best_validation_sharpe']:.3f}")
    sys_info = state.get("system", {})
    if sys_info.get("cpu_pct") is not None:
        lines.append(f"  CPU: {sys_info['cpu_pct']:.0f}%  RAM: {sys_info.get('ram_used_gb', '?')}/{sys_info.get('ram_total_gb', '?')} GB")
    lines.append("")
    if not state.get("active"):
        lines.append("  No active training.")
        lines.append("  Next: python -m hydra.data_sources.registry --audit --symbol XAUUSD --years 9")
    lines.append("=" * 60)
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry
# ─────────────────────────────────────────────────────────────────────────────

def load_latest_packet(state: dict) -> dict | None:
    run_id = state.get("run_id")
    if not run_id:
        return None
    tel_dir = RUNS_DIR / run_id / "telemetry" / "packets"
    if not tel_dir.exists():
        return None
    packets = sorted(tel_dir.glob("iteration_*.json"), reverse=True)
    if not packets:
        return None
    try:
        return json.loads(packets[0].read_text())
    except (json.JSONDecodeError, OSError):
        return None


def load_packet_by_iter(state: dict, iteration: int) -> dict | None:
    run_id = state.get("run_id")
    if not run_id:
        return None
    path = RUNS_DIR / run_id / "telemetry" / "packets" / f"iteration_{iteration:03d}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def render_firehose(state: dict) -> str:
    """Dense firehose rendering — fills terminal with real data."""
    lines = []
    lines.append("=" * 78)
    lines.append("  HYDRA 1000-SIGNAL CONTROL ROOM | FIREHOSE MODE")
    lines.append("=" * 78)

    status = state.get("status", "IDLE")
    lines.append(f"  Status: {status} | Phase: {state.get('phase')} | Iter: {state.get('iteration', 0)}/{state.get('max_iterations', 0)}")
    lines.append(f"  Run: {state.get('run_id', 'N/A')} | ETA: {state.get('eta_human', 'N/A')}")
    lines.append(f"  Task: {state.get('current_task', 'N/A')}")

    # Progress
    overall = state.get("progress_pct", 0) or 0
    phase = state.get("phase_progress_pct", 0) or 0
    lines.append(f"  Overall: [{'#' * int(overall / 2.5)}{'.' * (40 - int(overall / 2.5))}] {overall:.1f}%")
    lines.append(f"  Phase:   [{'#' * int(phase / 2.5)}{'.' * (40 - int(phase / 2.5))}] {phase:.1f}%")

    # Metrics preview
    mp = state.get("metrics_preview", {})
    lines.append(f"  Best Sharpe: {mp.get('best_validation_sharpe', 'N/A')} | Trades: {mp.get('trades_so_far', 0)} | OOS: {'LOCKED' if mp.get('current_oos_locked') else 'OPEN'}")
    lines.append("")

    # Latest telemetry packet
    pkt = load_latest_packet(state)
    if pkt:
        lines.append("─── LATEST TELEMETRY PACKET ─────────────────────────────────────────────")
        lines.append(f"  Iter: {pkt.get('iteration')} | Mode: {pkt.get('mode')} | Status: {pkt.get('status')}")

        # Timing
        t = pkt.get("timing", {})
        lines.append(f"  Timing: {t.get('iteration_seconds', 'N/A')}s/iter | {t.get('iterations_per_hour', 'N/A')} iter/h | elapsed: {t.get('elapsed_seconds', 0):.0f}s")

        # Data
        d = pkt.get("data", {})
        lines.append(f"  Data: {d.get('rows_total', 'N/A')} rows | {d.get('timeframe', 'N/A')} | close: {d.get('close_last', 'N/A')} | ret_std: {d.get('return_std', 'N/A')}")

        # Features
        f = pkt.get("features", {})
        lines.append(f"  Features: {f.get('feature_count', 'N/A')} total | const: {f.get('constant_feature_count', 'N/A')} | nan: {f.get('nan_feature_count', 'N/A')} | std_range: [{f.get('feature_std_min', 'N/A')}, {f.get('feature_std_max', 'N/A')}]")
        top_imp = f.get("top_importance_features", [])
        if top_imp:
            top3 = ", ".join(f"{fi['feature']}={fi['importance']:.4f}" for fi in top_imp[:3])
            lines.append(f"  Top features: {top3}")

        # Targets
        tgt = pkt.get("targets", {})
        lines.append(f"  Targets: {tgt.get('target_name', 'N/A')} | horizon: {tgt.get('label_horizon', 'N/A')} | pos%: {tgt.get('train_positive_pct', 'N/A')}%")

        # Model
        m = pkt.get("model", {})
        lines.append(f"  Model: {m.get('model_name', 'N/A')} | seed: {m.get('seed', 'N/A')} | n_est: {m.get('n_estimators', 'N/A')} | lr: {m.get('learning_rate', 'N/A')}")

        # Training
        tr = pkt.get("training", {})
        lines.append(f"  Train: trades={tr.get('train_trades', 'N/A')} | sharpe={tr.get('train_sharpe', 'N/A')} | PF={tr.get('train_profit_factor', 'N/A')} | DD={tr.get('train_max_drawdown', 'N/A')}%")

        # Validation
        v = pkt.get("validation", {})
        lines.append(f"  Valid: trades={v.get('validation_trades', 'N/A')} | sharpe={v.get('validation_sharpe', 'N/A')} | PF={v.get('validation_profit_factor', 'N/A')} | win={v.get('validation_win_rate', 'N/A')} | DD={v.get('validation_max_drawdown', 'N/A')}%")
        lines.append(f"         profit=${v.get('validation_total_profit', 'N/A')} | eq: {v.get('validation_equity_start', 'N/A')}→{v.get('validation_equity_end', 'N/A')}")

        # Predictions
        p = pkt.get("predictions", {})
        lines.append(f"  Preds: n={p.get('validation_prediction_count', 'N/A')} | prob: {p.get('validation_prob_mean', 'N/A')}±{p.get('validation_prob_std', 'N/A')} [{p.get('validation_prob_min', 'N/A')},{p.get('validation_prob_max', 'N/A')}]")
        lines.append(f"         long={p.get('validation_signal_long_count', 'N/A')} short={p.get('validation_signal_short_count', 'N/A')} flat={p.get('validation_signal_flat_count', 'N/A')}")

        # Calibration
        cal = pkt.get("calibration", {})
        lines.append(f"  Calib: brier={cal.get('brier_score', 'N/A')} | logloss={cal.get('log_loss', 'N/A')} | AUC={cal.get('auc', 'N/A')} | AP={cal.get('average_precision', 'N/A')}")

        # Confusion
        cf = pkt.get("confusion", {})
        lines.append(f"  Confusion: TP={cf.get('tp', 'N/A')} TN={cf.get('tn', 'N/A')} FP={cf.get('fp', 'N/A')} FN={cf.get('fn', 'N/A')} | acc={cf.get('accuracy', 'N/A')} | F1={cf.get('f1', 'N/A')}")

        # Trades
        td = pkt.get("trades", {})
        lines.append(f"  Trades: val={td.get('validation_trade_count', 'N/A')} | L={td.get('long_count', 'N/A')} S={td.get('short_count', 'N/A')} | best=${td.get('best_trade', 'N/A')} worst=${td.get('worst_trade', 'N/A')}")
        lines.append(f"          mean=${td.get('mean_trade', 'N/A')} med=${td.get('median_trade', 'N/A')} std=${td.get('std_trade', 'N/A')} | streak: W{td.get('win_streak_max', 'N/A')} L{td.get('loss_streak_max', 'N/A')}")

        # Risk
        rk = pkt.get("risk", {})
        lines.append(f"  Risk: VaR95={rk.get('var_95', 'N/A')} CVaR95={rk.get('cvar_95', 'N/A')} | skew={rk.get('skew', 'N/A')} kurt={rk.get('kurtosis', 'N/A')} | tail={rk.get('tail_ratio', 'N/A')}")

        # Deltas
        dl = pkt.get("deltas", {})
        lines.append(f"  Deltas: sharpe={dl.get('validation_sharpe_delta', 'N/A')} | PF={dl.get('validation_profit_factor_delta', 'N/A')} | trades={dl.get('validation_trades_delta', 'N/A')}")

        # Neural
        nn = pkt.get("neural", {})
        if nn.get("is_neural"):
            lines.append(f"  Neural: loss={nn.get('validation_loss_latest')} | grad_norm={nn.get('gradient_norm_mean')} | overfit_gap={nn.get('overfit_gap')}")
        else:
            lines.append(f"  Neural: N/A — {nn.get('reason', 'non-neural model')}")

    else:
        lines.append("  No telemetry packets yet.")

    lines.append("")

    # System
    sys_info = state.get("system", {})
    lines.append(f"─── SYSTEM ──────────────────────────────────────────────────────────────")
    lines.append(f"  CPU: {sys_info.get('cpu_pct', 'N/A')}% | RAM: {sys_info.get('ram_used_gb', 'N/A')}/{sys_info.get('ram_total_gb', 'N/A')} GB")
    if sys_info.get("gpu_available"):
        lines.append(f"  GPU: {sys_info.get('gpu_name', 'N/A')} | util: {sys_info.get('gpu_util_pct', 'N/A')}% | VRAM: {sys_info.get('gpu_vram_used_gb', 'N/A')}/{sys_info.get('gpu_vram_total_gb', 'N/A')} GB")

    # Modes
    modes = state.get("modes", {})
    if modes:
        lines.append(f"─── MODES ───────────────────────────────────────────────────────────────")
        for mname, minfo in modes.items():
            lines.append(f"  {mname.upper():10s} | {minfo.get('status', 'N/A'):10s} | {minfo.get('progress_pct', 0):.0f}% | sharpe={minfo.get('best_validation_sharpe', 'N/A')} | trades={minfo.get('trades', 0)}")

    # Events
    events = find_latest_events(state)
    if events:
        lines.append(f"─── EVENTS (last {min(len(events), 5)}) ──────────────────────────────────────────────")
        for ev in events[-5:]:
            ts_short = ev.get("ts", "")[-8:] if ev.get("ts") else ""
            lines.append(f"  [{ts_short}] {ev.get('level', 'INFO'):7s} {ev.get('message', '')[:70]}")

    # Warnings/errors
    if state.get("warnings"):
        lines.append(f"─── WARNINGS ────────────────────────────────────────────────────────────")
        for w in state["warnings"][-3:]:
            lines.append(f"  ! {w}")
    if state.get("last_error"):
        lines.append(f"  ERROR: {state['last_error']}")

    lines.append("=" * 78)
    return "\n".join(lines)


def cmd_telemetry_json(state: dict, iteration: str = "latest") -> None:
    if iteration == "latest":
        pkt = load_latest_packet(state)
    else:
        pkt = load_packet_by_iter(state, int(iteration))
    if pkt:
        print(json.dumps(pkt, indent=2, default=str))
    else:
        print(f"No telemetry packet found for iteration={iteration}")


def cmd_neural(state: dict) -> None:
    pkt = load_latest_packet(state)
    if not pkt:
        print("No telemetry packets found.")
        return
    nn = pkt.get("neural", {})
    print("=== NEURAL TELEMETRY ===")
    if nn.get("is_neural"):
        for k, v in nn.items():
            print(f"  {k}: {v}")
    else:
        print(f"  {nn.get('reason', 'N/A — non-neural model')}")


def cmd_features(state: dict) -> None:
    pkt = load_latest_packet(state)
    if not pkt:
        print("No telemetry packets found.")
        return
    f = pkt.get("features", {})
    print("=== FEATURE TELEMETRY ===")
    print(f"  Count: {f.get('feature_count')}")
    print(f"  Constants: {f.get('constant_feature_count')}")
    print(f"  NaN features: {f.get('nan_feature_count')}")
    print(f"  Std range: [{f.get('feature_std_min')}, {f.get('feature_std_max')}]")
    print(f"  Mean abs mean: {f.get('feature_mean_abs_mean')}")
    top = f.get("top_importance_features", [])
    if top:
        print(f"  Top importance:")
        for fi in top[:10]:
            print(f"    #{fi['rank']:2d} {fi['feature']:30s} = {fi['importance']:.6f} ({fi['model']})")


def cmd_predictions(state: dict) -> None:
    pkt = load_latest_packet(state)
    if not pkt:
        print("No telemetry packets found.")
        return
    p = pkt.get("predictions", {})
    print("=== PREDICTION TELEMETRY ===")
    print(f"  Validation predictions: {p.get('validation_prediction_count')}")
    print(f"  Prob: mean={p.get('validation_prob_mean')} std={p.get('validation_prob_std')}")
    print(f"  Prob: min={p.get('validation_prob_min')} max={p.get('validation_prob_max')}")
    print(f"  Percentiles: p05={p.get('validation_prob_p05')} p25={p.get('validation_prob_p25')} p50={p.get('validation_prob_p50')} p75={p.get('validation_prob_p75')} p95={p.get('validation_prob_p95')}")
    print(f"  Signals: long={p.get('validation_signal_long_count')} short={p.get('validation_signal_short_count')} flat={p.get('validation_signal_flat_count')}")
    cal = pkt.get("calibration", {})
    print(f"  Calibration: brier={cal.get('brier_score')} logloss={cal.get('log_loss')} AUC={cal.get('auc')}")
    cf = pkt.get("confusion", {})
    print(f"  Confusion: TP={cf.get('tp')} TN={cf.get('tn')} FP={cf.get('fp')} FN={cf.get('fn')} acc={cf.get('accuracy')} F1={cf.get('f1')}")


def cmd_trades(state: dict) -> None:
    pkt = load_latest_packet(state)
    if not pkt:
        print("No telemetry packets found.")
        return
    td = pkt.get("trades", {})
    print("=== TRADE TELEMETRY ===")
    for k, v in td.items():
        print(f"  {k}: {v}")


def main():
    parser = argparse.ArgumentParser(description="HYDRA Progress Dashboard")
    parser.add_argument("--watch", action="store_true", help="Live refresh mode")
    parser.add_argument("--refresh", type=float, default=1.0, help="Refresh interval seconds")
    parser.add_argument("--json", action="store_true", help="Print raw JSON state")
    parser.add_argument("--logs", action="store_true", help="Show recent logs")
    parser.add_argument("--tail", type=int, default=50, help="Number of log lines")
    parser.add_argument("--last-run", action="store_true", help="Show last run info")
    parser.add_argument("--full", action="store_true", help="Full dashboard")
    parser.add_argument("--firehose", action="store_true", help="Maximum density firehose mode")
    parser.add_argument("--telemetry-json", action="store_true", help="Print telemetry packet JSON")
    parser.add_argument("--iteration", default="latest", help="Iteration number or 'latest'")
    parser.add_argument("--neural", action="store_true", help="Neural network telemetry")
    parser.add_argument("--features", action="store_true", help="Feature telemetry")
    parser.add_argument("--predictions", action="store_true", help="Prediction telemetry")
    parser.add_argument("--trades", action="store_true", help="Trade telemetry")
    parser.add_argument("--errors", action="store_true", help="Error log")
    parser.add_argument("--artifacts", action="store_true", help="List artifacts")
    parser.add_argument("--files", action="store_true", help="File freshness")
    parser.add_argument("--system", action="store_true", help="System stats")
    parser.add_argument("--iteration-table", action="store_true", help="All iterations table")
    parser.add_argument("--curves", action="store_true", help="Equity curve paths")
    args = parser.parse_args()

    if args.json:
        state = load_state()
        print(json.dumps(state, indent=2, default=str))
        return

    if args.telemetry_json:
        state = load_state()
        cmd_telemetry_json(state, args.iteration)
        return

    if args.neural:
        cmd_neural(load_state())
        return

    if args.features:
        cmd_features(load_state())
        return

    if args.predictions:
        cmd_predictions(load_state())
        return

    if args.trades:
        cmd_trades(load_state())
        return

    if args.logs or args.errors:
        state = load_state()
        log_path = find_latest_log(state)
        if log_path:
            lines = tail_file(log_path, args.tail)
            if lines:
                for line in lines:
                    print(line)
            else:
                print("Log file empty.")
        else:
            print("No logs found.")
        return

    if args.system:
        from hydra.utils.system_monitor import get_system_stats
        stats = get_system_stats()
        for k, v in stats.items():
            print(f"  {k}: {v}")
        return

    if args.last_run:
        state = load_state()
        run_id = state.get("run_id")
        if not run_id:
            candidates = sorted(RUNS_DIR.glob("hydra_*"), key=lambda p: p.stat().st_mtime, reverse=True)
            if candidates:
                run_id = candidates[0].name
        if run_id:
            print(f"Last run: {run_id}")
            summary = RUNS_DIR / run_id / "summary_report.md"
            if summary.exists():
                print(summary.read_text()[:3000])
            else:
                print("No summary report found.")
        else:
            print("No runs found.")
        return

    if args.watch:
        use_firehose = args.firehose or args.full
        try:
            if use_firehose:
                # Plain firehose — no Rich Live needed, just ANSI clear
                while True:
                    state = load_state()
                    print("\033[2J\033[H" + render_firehose(state), flush=True)
                    time.sleep(args.refresh)
            else:
                from rich.live import Live
                from rich.console import Console
                console = Console()
                with Live(render_rich(load_state()), console=console,
                          refresh_per_second=1.0 / args.refresh, screen=False) as live:
                    while True:
                        state = load_state()
                        live.update(render_rich(state))
                        time.sleep(args.refresh)
        except ImportError:
            while True:
                state = load_state()
                print("\033[2J\033[H" + render_firehose(state), flush=True)
                time.sleep(args.refresh)
        except KeyboardInterrupt:
            print("\nDashboard closed.")
        return

    # One-shot render
    state = load_state()
    if args.firehose or args.full:
        print(render_firehose(state))
    else:
        try:
            from rich.console import Console
            console = Console()
            console.print(render_rich(state))
        except ImportError:
            print(render_plain(state))


if __name__ == "__main__":
    main()
