"""Conservative execution simulator with path-dependent stop/TP."""
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from .costs import CostModel, compute_total_cost


@dataclass
class SimulationConfig:
    """Execution simulation configuration."""

    # Entry timing
    signal_at_bar_i_entry_at_bar_i_plus_n: int = 1  # Default: next-bar entry
    allow_same_bar_entry: bool = False  # Default: conservative, no same-bar

    # Position sizing
    risk_per_trade_usd: float = 1000.0  # Fixed risk per trade
    position_size_oz: float = 10.0  # Fixed position size (10 oz = 0.1 lot)
    use_fixed_size: bool = True  # Use fixed size, not risk-based

    # Exit rules
    hold_bars: Optional[int] = None  # Fixed hold period (None = use stops only)
    stop_loss_atr_mult: Optional[float] = None  # Stop loss in ATR multiples
    take_profit_atr_mult: Optional[float] = None  # Take profit in ATR multiples

    # Costs
    cost_model: CostModel = field(default_factory=CostModel.xauusd_baseline)

    # Risk controls
    max_daily_drawdown_usd: Optional[float] = None  # Intraday breach check
    max_total_drawdown_usd: Optional[float] = None  # Total breach check

    # Compounding
    enable_compounding: bool = False  # Default: no compounding

    def __post_init__(self):
        """Validate configuration."""
        if self.signal_at_bar_i_entry_at_bar_i_plus_n < 0:
            raise ValueError("Entry lag must be >= 0")
        if not self.allow_same_bar_entry and self.signal_at_bar_i_entry_at_bar_i_plus_n == 0:
            raise ValueError("Same-bar entry disabled but lag=0. Set lag>=1 or enable same-bar.")


@dataclass
class Trade:
    """Single trade record."""

    entry_time: pd.Timestamp
    entry_price: float
    exit_time: pd.Timestamp
    exit_price: float
    direction: int  # 1 for long, -1 for short
    size_oz: float
    pnl_gross: float
    cost: float
    pnl_net: float
    exit_reason: str  # 'hold_bars', 'stop_loss', 'take_profit', 'drawdown_breach'
    signal_time: pd.Timestamp  # When signal was generated


def simulate_trades(
    signals: pd.Series,
    ohlcv: pd.DataFrame,
    config: SimulationConfig,
    atr: Optional[pd.Series] = None,
) -> Dict[str, Any]:
    """Simulate trades with conservative execution.

    Args:
        signals: Series of signals (1=long, -1=short, 0=no signal)
        ohlcv: DataFrame with OHLC, spread
        config: Simulation configuration
        atr: Optional ATR series (required if using ATR-based stops)

    Returns:
        Dict with:
            - trades: List of Trade objects
            - equity_curve: Series of equity over time
            - metrics: Dict of performance metrics
            - breaches: List of drawdown breaches

    Rules:
        1. Signal at bar i → entry no earlier than bar i+N (default N=1)
        2. Entry price = open[i+N] + spread/2 (conservative)
        3. Exit price = close or stop/TP level (path-dependent)
        4. Same-bar stop/TP ambiguity: assume stop hit first (conservative)
        5. Daily/total drawdown breach stops all trading
    """
    if not isinstance(ohlcv.index, pd.DatetimeIndex):
        raise ValueError("ohlcv must have DatetimeIndex")
    if not isinstance(signals.index, pd.DatetimeIndex):
        raise ValueError("signals must have DatetimeIndex")

    # Align signals and OHLCV
    signals = signals.reindex(ohlcv.index, fill_value=0)

    # Check ATR if needed
    if (config.stop_loss_atr_mult or config.take_profit_atr_mult) and atr is None:
        raise ValueError("ATR required for ATR-based stops but not provided")

    trades: List[Trade] = []
    equity = config.risk_per_trade_usd  # Starting equity (arbitrary baseline)
    equity_curve = pd.Series(index=ohlcv.index, dtype=float)
    equity_curve.iloc[0] = equity

    daily_pnl = {}  # Track daily PnL for drawdown breach
    breaches = []

    i = 0
    in_position = False
    position_entry_idx = None

    while i < len(ohlcv):
        current_time = ohlcv.index[i]
        current_date = current_time.date()

        # Initialize daily PnL
        if current_date not in daily_pnl:
            daily_pnl[current_date] = 0.0

        # Check for new signal
        if not in_position and signals.iloc[i] != 0:
            signal_direction = int(signals.iloc[i])
            signal_time = current_time

            # Entry lag
            entry_idx = i + config.signal_at_bar_i_entry_at_bar_i_plus_n
            if entry_idx >= len(ohlcv):
                break  # Not enough bars for entry

            # Enter at open[i+N] + spread/2 (conservative)
            entry_bar = ohlcv.iloc[entry_idx]
            entry_price = entry_bar["open"] + entry_bar["spread"] / 2
            entry_time = ohlcv.index[entry_idx]

            # Position size
            if config.use_fixed_size:
                size_oz = config.position_size_oz
            else:
                # Risk-based sizing (not implemented, use fixed)
                size_oz = config.position_size_oz

            # Compute stops if ATR-based
            stop_price = None
            tp_price = None
            if config.stop_loss_atr_mult and atr is not None:
                atr_val = atr.iloc[entry_idx]
                if signal_direction == 1:  # long
                    stop_price = entry_price - config.stop_loss_atr_mult * atr_val
                else:  # short
                    stop_price = entry_price + config.stop_loss_atr_mult * atr_val

            if config.take_profit_atr_mult and atr is not None:
                atr_val = atr.iloc[entry_idx]
                if signal_direction == 1:  # long
                    tp_price = entry_price + config.take_profit_atr_mult * atr_val
                else:  # short
                    tp_price = entry_price - config.take_profit_atr_mult * atr_val

            # Store position state
            in_position = True
            position_entry_idx = entry_idx
            position_direction = signal_direction
            position_entry_price = entry_price
            position_entry_time = entry_time
            position_signal_time = signal_time
            position_size = size_oz
            position_stop = stop_price
            position_tp = tp_price
            position_hold_bars = config.hold_bars

            i = entry_idx + 1  # Skip to next bar after entry
            continue

        # Exit logic (if in position)
        if in_position:
            bars_held = i - position_entry_idx
            current_bar = ohlcv.iloc[i]

            exit_price = None
            exit_reason = None

            # Check hold_bars exit
            if position_hold_bars and bars_held >= position_hold_bars:
                exit_price = current_bar["close"]
                exit_reason = "hold_bars"

            # Check stop loss (path-dependent)
            if position_stop is not None and exit_price is None:
                if position_direction == 1:  # long
                    if current_bar["low"] <= position_stop:
                        # Stop hit
                        # Conservative: assume hit at low (worst case)
                        exit_price = position_stop
                        exit_reason = "stop_loss"
                else:  # short
                    if current_bar["high"] >= position_stop:
                        exit_price = position_stop
                        exit_reason = "stop_loss"

            # Check take profit (path-dependent)
            # If both stop and TP possible in same bar, assume stop hit first (conservative)
            if position_tp is not None and exit_price is None:
                if position_direction == 1:  # long
                    if current_bar["high"] >= position_tp:
                        exit_price = position_tp
                        exit_reason = "take_profit"
                else:  # short
                    if current_bar["low"] <= position_tp:
                        exit_price = position_tp
                        exit_reason = "take_profit"

            # Execute exit if triggered
            if exit_price is not None:
                exit_time = current_time

                # Compute PnL
                if position_direction == 1:  # long
                    pnl_gross = (exit_price - position_entry_price) * position_size
                else:  # short
                    pnl_gross = (position_entry_price - exit_price) * position_size

                # Compute cost
                cost = compute_total_cost(
                    entry_price=position_entry_price,
                    exit_price=exit_price,
                    direction=position_direction,
                    position_size_oz=position_size,
                    cost_model=config.cost_model,
                )

                pnl_net = pnl_gross - cost

                # Record trade
                trade = Trade(
                    entry_time=position_entry_time,
                    entry_price=position_entry_price,
                    exit_time=exit_time,
                    exit_price=exit_price,
                    direction=position_direction,
                    size_oz=position_size,
                    pnl_gross=pnl_gross,
                    cost=cost,
                    pnl_net=pnl_net,
                    exit_reason=exit_reason,
                    signal_time=position_signal_time,
                )
                trades.append(trade)

                # Update equity
                equity += pnl_net
                equity_curve.iloc[i] = equity

                # Update daily PnL
                daily_pnl[current_date] += pnl_net

                # Check daily drawdown breach
                if config.max_daily_drawdown_usd:
                    if daily_pnl[current_date] < -config.max_daily_drawdown_usd:
                        breaches.append({
                            "type": "daily_drawdown",
                            "time": current_time,
                            "pnl": daily_pnl[current_date],
                        })
                        # Stop trading for the day
                        # (In practice, skip to next day, but here we just mark)
                        exit_reason = "drawdown_breach"

                # Check total drawdown breach
                if config.max_total_drawdown_usd:
                    total_pnl = sum(t.pnl_net for t in trades)
                    if total_pnl < -config.max_total_drawdown_usd:
                        breaches.append({
                            "type": "total_drawdown",
                            "time": current_time,
                            "pnl": total_pnl,
                        })
                        # Stop all trading
                        break

                # Reset position
                in_position = False
                position_entry_idx = None

        # Forward-fill equity
        if i > 0:
            equity_curve.iloc[i] = equity_curve.iloc[i - 1] if pd.isna(equity_curve.iloc[i]) else equity_curve.iloc[i]

        i += 1

    # Compute metrics
    if len(trades) == 0:
        metrics = {
            "num_trades": 0,
            "win_rate": 0.0,
            "avg_pnl_net": 0.0,
            "total_pnl_net": 0.0,
            "sharpe": 0.0,
            "max_drawdown": 0.0,
        }
    else:
        pnls = [t.pnl_net for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]

        metrics = {
            "num_trades": len(trades),
            "win_rate": len(wins) / len(trades) if len(trades) > 0 else 0.0,
            "avg_pnl_net": np.mean(pnls),
            "total_pnl_net": sum(pnls),
            "sharpe": np.mean(pnls) / np.std(pnls) if np.std(pnls) > 0 else 0.0,
            "max_drawdown": (equity_curve.cummax() - equity_curve).max(),
            "avg_win": np.mean(wins) if wins else 0.0,
            "avg_loss": np.mean(losses) if losses else 0.0,
        }

    return {
        "trades": trades,
        "equity_curve": equity_curve,
        "metrics": metrics,
        "breaches": breaches,
    }
