"""Triple-barrier labeling with cost awareness for BOI."""
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Tuple, Optional


@dataclass
class CostModel:
    """Transaction cost model."""
    spread_points: float = 0.30
    slippage_points: float = 0.10
    commission_per_lot: float = 7.0
    lot_size: float = 100.0

    def total_cost_per_oz(self) -> float:
        """Total round-trip cost per ounce."""
        price_cost = (self.spread_points + self.slippage_points) * 2  # Round-trip
        commission_cost = (self.commission_per_lot * 2) / self.lot_size  # Per oz
        return price_cost + commission_cost


def create_triple_barrier_labels(
    ohlcv: pd.DataFrame,
    atr: pd.Series,
    horizon_bars: int = 8,
    stop_atr_mult: float = 1.0,
    target_atr_mult: float = 2.0,
    entry_lag: int = 1,
    cost_model: Optional[CostModel] = None,
    ambiguity_handling: str = "conservative",
) -> Tuple[pd.Series, pd.DataFrame]:
    """Create triple-barrier labels with cost awareness.

    Args:
        ohlcv: OHLCV DataFrame with DatetimeIndex
        atr: ATR series (aligned to ohlcv)
        horizon_bars: Max holding period
        stop_atr_mult: Stop loss in ATR multiples
        target_atr_mult: Take profit in ATR multiples
        entry_lag: Signal at bar i → entry at bar i+N
        cost_model: Transaction cost model (optional)
        ambiguity_handling: "conservative" = stop first if both touched

    Returns:
        Tuple of (labels, metadata_df)
        - labels: Series of {0: short, 1: skip, 2: long}
        - metadata: DataFrame with exit_reason, bars_held, gross_pnl, net_pnl
    """
    if cost_model is None:
        cost_model = CostModel()

    cost_per_oz = cost_model.total_cost_per_oz()

    labels = pd.Series(1, index=ohlcv.index, dtype=int)  # Default: skip
    metadata = pd.DataFrame(index=ohlcv.index)
    metadata['exit_reason'] = 'none'
    metadata['bars_held'] = 0
    metadata['gross_pnl'] = 0.0
    metadata['net_pnl'] = 0.0

    for i in range(len(ohlcv) - horizon_bars - entry_lag):
        signal_time = ohlcv.index[i]
        entry_idx = i + entry_lag
        entry_time = ohlcv.index[entry_idx]
        entry_price = ohlcv.iloc[entry_idx]['open']

        atr_val = atr.iloc[entry_idx]
        if pd.isna(atr_val) or atr_val <= 0:
            continue

        # Stop/target levels
        stop_long = entry_price - stop_atr_mult * atr_val
        target_long = entry_price + target_atr_mult * atr_val
        stop_short = entry_price + stop_atr_mult * atr_val
        target_short = entry_price - target_atr_mult * atr_val

        # Scan forward horizon
        exit_idx_long = None
        exit_reason_long = None
        exit_idx_short = None
        exit_reason_short = None

        for j in range(1, horizon_bars + 1):
            if entry_idx + j >= len(ohlcv):
                break

            bar = ohlcv.iloc[entry_idx + j]

            # Check long
            if exit_idx_long is None:
                stop_hit = bar['low'] <= stop_long
                target_hit = bar['high'] >= target_long

                if stop_hit and target_hit:
                    # Ambiguous
                    if ambiguity_handling == "conservative":
                        exit_idx_long = entry_idx + j
                        exit_reason_long = 'stop'
                elif stop_hit:
                    exit_idx_long = entry_idx + j
                    exit_reason_long = 'stop'
                elif target_hit:
                    exit_idx_long = entry_idx + j
                    exit_reason_long = 'target'

            # Check short
            if exit_idx_short is None:
                stop_hit = bar['high'] >= stop_short
                target_hit = bar['low'] <= target_short

                if stop_hit and target_hit:
                    # Ambiguous
                    if ambiguity_handling == "conservative":
                        exit_idx_short = entry_idx + j
                        exit_reason_short = 'stop'
                elif stop_hit:
                    exit_idx_short = entry_idx + j
                    exit_reason_short = 'stop'
                elif target_hit:
                    exit_idx_short = entry_idx + j
                    exit_reason_short = 'target'

        # Timeout if no exit
        if exit_idx_long is None:
            exit_idx_long = entry_idx + horizon_bars
            exit_reason_long = 'timeout'

        if exit_idx_short is None:
            exit_idx_short = entry_idx + horizon_bars
            exit_reason_short = 'timeout'

        # Compute PnL
        exit_price_long = ohlcv.iloc[exit_idx_long]['close'] if exit_reason_long == 'timeout' else (
            target_long if exit_reason_long == 'target' else stop_long
        )
        gross_pnl_long = (exit_price_long - entry_price)
        net_pnl_long = gross_pnl_long - cost_per_oz

        exit_price_short = ohlcv.iloc[exit_idx_short]['close'] if exit_reason_short == 'timeout' else (
            target_short if exit_reason_short == 'target' else stop_short
        )
        gross_pnl_short = (entry_price - exit_price_short)
        net_pnl_short = gross_pnl_short - cost_per_oz

        # Choose best direction
        if net_pnl_long > 0 and net_pnl_short <= 0:
            labels.iloc[i] = 2  # Long
            metadata.iloc[i] = {
                'exit_reason': exit_reason_long,
                'bars_held': exit_idx_long - entry_idx,
                'gross_pnl': gross_pnl_long,
                'net_pnl': net_pnl_long,
            }
        elif net_pnl_short > 0 and net_pnl_long <= 0:
            labels.iloc[i] = 0  # Short
            metadata.iloc[i] = {
                'exit_reason': exit_reason_short,
                'bars_held': exit_idx_short - entry_idx,
                'gross_pnl': gross_pnl_short,
                'net_pnl': net_pnl_short,
            }
        elif net_pnl_long > net_pnl_short:
            labels.iloc[i] = 2  # Long
            metadata.iloc[i] = {
                'exit_reason': exit_reason_long,
                'bars_held': exit_idx_long - entry_idx,
                'gross_pnl': gross_pnl_long,
                'net_pnl': net_pnl_long,
            }
        elif net_pnl_short > net_pnl_long:
            labels.iloc[i] = 0  # Short
            metadata.iloc[i] = {
                'exit_reason': exit_reason_short,
                'bars_held': exit_idx_short - entry_idx,
                'gross_pnl': gross_pnl_short,
                'net_pnl': net_pnl_short,
            }
        else:
            # Both equal or both negative → skip
            labels.iloc[i] = 1  # Skip
            metadata.iloc[i] = {
                'exit_reason': 'skip',
                'bars_held': 0,
                'gross_pnl': 0.0,
                'net_pnl': 0.0,
            }

    return labels, metadata
