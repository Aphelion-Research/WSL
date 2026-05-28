"""Cost sensitivity analysis."""
import pandas as pd
from typing import Dict, Any, List
from ..execution.simulator import simulate_trades, SimulationConfig
from ..execution.costs import CostModel


def run_cost_sensitivity(
    signals: pd.Series,
    ohlcv: pd.DataFrame,
    base_config: SimulationConfig,
    atr: pd.Series = None,
    cost_multipliers: List[float] = None,
) -> Dict[str, Any]:
    """Run cost sensitivity analysis.

    Args:
        signals: Trading signals
        ohlcv: OHLCV data
        base_config: Base simulation config
        atr: ATR series (optional)
        cost_multipliers: List of cost multipliers (default: [0, 0.5, 1, 2, 3])

    Returns:
        Dict with results for each cost multiplier
    """
    if cost_multipliers is None:
        cost_multipliers = [0.0, 0.5, 1.0, 2.0, 3.0]

    results = {}

    for mult in cost_multipliers:
        # Scale costs
        scaled_config = SimulationConfig(
            signal_at_bar_i_entry_at_bar_i_plus_n=base_config.signal_at_bar_i_entry_at_bar_i_plus_n,
            allow_same_bar_entry=base_config.allow_same_bar_entry,
            risk_per_trade_usd=base_config.risk_per_trade_usd,
            position_size_oz=base_config.position_size_oz,
            use_fixed_size=base_config.use_fixed_size,
            hold_bars=base_config.hold_bars,
            stop_loss_atr_mult=base_config.stop_loss_atr_mult,
            take_profit_atr_mult=base_config.take_profit_atr_mult,
            cost_model=base_config.cost_model.scale(mult),
            max_daily_drawdown_usd=base_config.max_daily_drawdown_usd,
            max_total_drawdown_usd=base_config.max_total_drawdown_usd,
            enable_compounding=base_config.enable_compounding,
        )

        result = simulate_trades(signals, ohlcv, scaled_config, atr)

        results[f"{mult}x"] = {
            "metrics": result["metrics"],
            "num_trades": len(result["trades"]),
            "total_pnl_net": result["metrics"]["total_pnl_net"],
            "sharpe": result["metrics"]["sharpe"],
        }

    # Compute cost degradation
    baseline = results["1.0x"]
    degradation = []

    for mult in cost_multipliers:
        key = f"{mult}x"
        if key in results:
            sharpe_ratio = results[key]["sharpe"] / baseline["sharpe"] if baseline["sharpe"] != 0 else 0
            pnl_ratio = results[key]["total_pnl_net"] / baseline["total_pnl_net"] if baseline["total_pnl_net"] != 0 else 0

            degradation.append({
                "multiplier": mult,
                "sharpe_ratio": sharpe_ratio,
                "pnl_ratio": pnl_ratio,
                "sharpe": results[key]["sharpe"],
                "pnl": results[key]["total_pnl_net"],
            })

    results["summary"] = {
        "degradation": degradation,
        "robust_to_2x_costs": results["2.0x"]["total_pnl_net"] > 0,
        "robust_to_3x_costs": results["3.0x"]["total_pnl_net"] > 0,
    }

    return results
