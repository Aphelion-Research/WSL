#!/usr/bin/env python3
"""
HYDRA Results Summarizer - Rich table of best configs.
"""
import csv
import sys
from pathlib import Path

try:
    from rich.console import Console
    from rich.table import Table
except ImportError:
    print("ERROR: Rich not installed. Run: bash scripts/install_rich_tools.sh")
    sys.exit(1)


def load_results(csv_path: str):
    """Load results CSV."""
    rows = []
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("model_type") == "baseline":
                continue
            rows.append(row)
    return rows


def main():
    console = Console()
    csv_path = "runs/hydra_cpp_288b_results.csv"

    if not Path(csv_path).exists():
        console.print(f"[red]Results not found: {csv_path}[/red]")
        sys.exit(1)

    rows = load_results(csv_path)

    # Sort by edge, then excess, then return
    edge_confirmed = [r for r in rows if r.get("model_edge_verdict") == "EDGE_CONFIRMED"]
    baseline_dom = [r for r in rows if r.get("model_edge_verdict") == "BASELINE_DOMINATED"]
    no_trade = [r for r in rows if r.get("model_edge_verdict") == "NO_TRADE"]
    signal_invalid = [r for r in rows if r.get("model_edge_verdict") == "SIGNAL_INVALID"]

    console.print(f"\n[bold cyan]HYDRA Results Summary[/bold cyan]")
    console.print(f"Total configs: {len(rows)}")
    console.print(f"EDGE_CONFIRMED: [green]{len(edge_confirmed)}[/green]")
    console.print(f"BASELINE_DOMINATED: [yellow]{len(baseline_dom)}[/yellow]")
    console.print(f"NO_TRADE: [yellow]{len(no_trade)}[/yellow]")
    console.print(f"SIGNAL_INVALID: [red]{len(signal_invalid)}[/red]")

    if edge_confirmed:
        console.print("\n[bold green]Top EDGE_CONFIRMED Configs[/bold green]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Config", style="cyan", width=30)
        table.add_column("Return %", justify="right", style="green")
        table.add_column("Baseline %", justify="right", style="yellow")
        table.add_column("Excess %", justify="right", style="blue")
        table.add_column("Trades", justify="right")
        table.add_column("Win %", justify="right")
        table.add_column("PF", justify="right")
        table.add_column("MaxDD %", justify="right")

        sorted_confirmed = sorted(edge_confirmed, key=lambda r: float(r.get("model_excess_return_pct", 0)), reverse=True)
        for row in sorted_confirmed[:10]:
            table.add_row(
                row.get("config", ""),
                f"{float(row.get('return_pct', 0)) * 100:.2f}",
                f"{float(row.get('best_baseline_return_pct', 0)) * 100:.2f}",
                f"{float(row.get('model_excess_return_pct', 0)) * 100:.2f}",
                row.get("total_trades", "0"),
                f"{float(row.get('win_rate', 0)) * 100:.1f}",
                f"{float(row.get('profit_factor', 0)):.2f}",
                f"{float(row.get('max_drawdown_pct', 0)) * 100:.1f}",
            )
        console.print(table)

    if baseline_dom:
        console.print("\n[bold yellow]Top BASELINE_DOMINATED Configs (by raw return)[/bold yellow]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Config", style="cyan", width=30)
        table.add_column("Return %", justify="right", style="green")
        table.add_column("Baseline %", justify="right", style="yellow")
        table.add_column("Excess %", justify="right", style="blue")
        table.add_column("Trades", justify="right")

        sorted_dom = sorted(baseline_dom, key=lambda r: float(r.get("return_pct", 0)), reverse=True)
        for row in sorted_dom[:5]:
            table.add_row(
                row.get("config", ""),
                f"{float(row.get('return_pct', 0)) * 100:.2f}",
                f"{float(row.get('best_baseline_return_pct', 0)) * 100:.2f}",
                f"{float(row.get('model_excess_return_pct', 0)) * 100:.2f}",
                row.get("total_trades", "0"),
            )
        console.print(table)


if __name__ == "__main__":
    main()
