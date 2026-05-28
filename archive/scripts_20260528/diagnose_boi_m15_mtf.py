"""Extended diagnostics for BOI M15 MTF.

Regime breakdown, baselines, detailed stability.

Usage:
    python scripts/diagnose_boi_m15_mtf.py [--config CONFIG_PATH]
"""
import sys
import yaml
import json
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
import xgboost as xgb

sys.path.insert(0, str(Path(__file__).parent.parent))

from boi.data import load_all_timeframes, split_by_date
from boi.features import build_all_features
from research_core.execution import simulate_trades, SimulationConfig, CostModel


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='config/models/boi_m15_mtf.yaml')
    args = parser.parse_args()

    print("=" * 60)
    print("BOI M15 MTF Diagnostics")
    print("=" * 60)

    with open(args.config) as f:
        config = yaml.safe_load(f)

    output_dir = Path(config['output']['base_dir'])
    model_path = output_dir / config['output']['model_file']

    if not model_path.exists():
        print(f"✗ Model not found at {model_path}")
        return

    # Load data
    print("\nLoading data...")
    data = load_all_timeframes(config)
    m15 = data['m15']

    # Build features
    print("Building features...")
    features = build_all_features(
        m15,
        data.get('m5'),
        data.get('h1'),
        data.get('h4'),
        data.get('d1'),
    )

    # Load model
    print("Loading model...")
    model = xgb.Booster()
    model.load_model(str(model_path))

    # Split
    splits = config['splits']
    _, _, oos_features = split_by_date(
        features,
        splits['train_start'], splits['train_end'],
        splits['val_start'], splits['val_end'],
        splits['oos_start'], splits['oos_end'],
    )
    _, _, oos_m15 = split_by_date(
        m15,
        splits['train_start'], splits['train_end'],
        splits['val_start'], splits['val_end'],
        splits['oos_start'], splits['oos_end'],
    )

    # Predict
    print("Generating predictions...")
    doos = xgb.DMatrix(oos_features.dropna())
    oos_pred = model.predict(doos)

    oos_signal_score = pd.Series(
        oos_pred[:, 2] - oos_pred[:, 0],
        index=oos_features.dropna().index
    )

    oos_signals = pd.Series(0, index=oos_signal_score.index)
    oos_signals[oos_signal_score > 0.1] = 1

    # ATR
    tr = pd.concat([
        oos_m15['high'] - oos_m15['low'],
        (oos_m15['high'] - oos_m15['close'].shift(1)).abs(),
        (oos_m15['low'] - oos_m15['close'].shift(1)).abs()
    ], axis=1).max(axis=1)
    oos_atr = tr.rolling(14).mean()

    # Simulate
    exec_config = config['execution']
    sim_config = SimulationConfig(
        signal_at_bar_i_entry_at_bar_i_plus_n=exec_config['entry_lag'],
        hold_bars=exec_config['hold_bars'],
        stop_loss_atr_mult=exec_config['stop_atr_mult'],
        take_profit_atr_mult=exec_config['target_atr_mult'],
        cost_model=CostModel(**exec_config['cost_model']),
        position_size_oz=exec_config['position_size_oz'],
    )

    result = simulate_trades(oos_signals, oos_m15, sim_config, oos_atr)

    print("\n" + "=" * 60)
    print("REGIME BREAKDOWN (OOS)")
    print("=" * 60)

    # Monthly breakdown
    print("\nMonthly PnL:")
    trades_df = pd.DataFrame([{
        'exit_time': t.exit_time,
        'pnl_net': t.pnl_net,
    } for t in result['trades']])

    if len(trades_df) > 0:
        trades_df['month'] = pd.to_datetime(trades_df['exit_time']).dt.to_period('M')
        monthly = trades_df.groupby('month')['pnl_net'].agg(['sum', 'count'])
        monthly.columns = ['pnl', 'trades']
        monthly['avg'] = monthly['pnl'] / monthly['trades']

        for month, row in monthly.iterrows():
            print(f"  {month}: ${row['pnl']:.2f} ({int(row['trades'])} trades, avg ${row['avg']:.2f})")

    # Session breakdown
    print("\nSession Breakdown:")
    if len(trades_df) > 0:
        trades_df['hour'] = pd.to_datetime(trades_df['exit_time']).dt.hour

        trades_df['session'] = 'late'
        trades_df.loc[(trades_df['hour'] >= 0) & (trades_df['hour'] < 8), 'session'] = 'asia'
        trades_df.loc[(trades_df['hour'] >= 8) & (trades_df['hour'] < 16), 'session'] = 'london'
        trades_df.loc[(trades_df['hour'] >= 13) & (trades_df['hour'] < 21), 'session'] = 'ny'

        session_stats = trades_df.groupby('session')['pnl_net'].agg(['sum', 'count', 'mean'])
        session_stats.columns = ['pnl', 'trades', 'avg']

        for session, row in session_stats.iterrows():
            print(f"  {session}: ${row['pnl']:.2f} ({int(row['trades'])} trades, avg ${row['avg']:.2f})")

    # Trade distribution
    print("\n" + "=" * 60)
    print("TRADE DISTRIBUTION")
    print("=" * 60)

    if len(result['trades']) > 0:
        pnls = [t.pnl_net for t in result['trades']]
        print(f"\nAll trades: {len(pnls)}")
        print(f"  Mean: ${np.mean(pnls):.2f}")
        print(f"  Median: ${np.median(pnls):.2f}")
        print(f"  Std: ${np.std(pnls):.2f}")
        print(f"  Min: ${np.min(pnls):.2f}")
        print(f"  Max: ${np.max(pnls):.2f}")

        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]

        print(f"\nWins: {len(wins)} ({len(wins)/len(pnls)*100:.1f}%)")
        if wins:
            print(f"  Mean: ${np.mean(wins):.2f}")
            print(f"  Max: ${np.max(wins):.2f}")

        print(f"\nLosses: {len(losses)} ({len(losses)/len(pnls)*100:.1f}%)")
        if losses:
            print(f"  Mean: ${np.mean(losses):.2f}")
            print(f"  Min: ${np.min(losses):.2f}")

        # Top/bottom trades
        sorted_pnls = sorted(pnls, reverse=True)
        print(f"\nTop 5 trades: ${sum(sorted_pnls[:5]):.2f} ({sum(sorted_pnls[:5])/sum(pnls)*100:.1f}% of total)")
        print(f"Bottom 5 trades: ${sum(sorted_pnls[-5:]):.2f}")

    # Save diagnostics
    diagnostics = {
        'monthly': monthly.to_dict() if len(trades_df) > 0 else {},
        'session': session_stats.to_dict() if len(trades_df) > 0 else {},
        'trade_distribution': {
            'count': len(pnls) if len(result['trades']) > 0 else 0,
            'mean': float(np.mean(pnls)) if len(result['trades']) > 0 else 0,
            'median': float(np.median(pnls)) if len(result['trades']) > 0 else 0,
            'std': float(np.std(pnls)) if len(result['trades']) > 0 else 0,
        },
    }

    diag_path = output_dir / config['output']['diagnostics_report']
    with open(diag_path, 'w') as f:
        json.dump(diagnostics, f, indent=2)
    print(f"\n✓ Diagnostics saved to {diag_path}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
