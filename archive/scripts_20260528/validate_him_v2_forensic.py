"""
Forensic Validation: Him V2 MultiScale
======================================
Validate locked Him V2 model with research_core diagnostics.

Train: 2015-2024
OOS: 2024-2026

No optimization. No tuning. Locked config from walk_forward results:
- Threshold: 0.65 (Conservative, best stability)
- Hold: 16 bars (80 min)
- Stop: 1.5 ATR
- TP: 3.0 ATR
"""
import pandas as pd
import numpy as np
import xgboost as xgb
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from research_core.execution import SimulationConfig, CostModel
from research_core.diagnostics import run_model_forensics
from research_core.data_contracts import validate_ohlcv


# Paths
DATA_PATH = Path("data/mt5_history/XAUUSD_M5_dukascopy.parquet")
MODEL_PATH = Path("models/Him/Him_V2_MultiScale.json")
OUTPUT_DIR = Path("output_him_v2/forensic_validation")
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

# Locked config (from multiscale_retrain_results.json Conservative config)
LOCKED_CONFIG = {
    'threshold': 0.65,
    'hold_bars': 16,  # 80 min
    'stop_atr_mult': 1.5,
    'tp_atr_mult': 3.0,
}

# Train/OOS split
TRAIN_END = "2023-12-31"
OOS_START = "2024-01-01"


def build_multiscale_features(m5):
    """Build multi-timeframe features for Him V2."""
    close = m5['close']
    high = m5['high']
    low = m5['low']
    volume = m5['tick_volume']
    spread = m5['spread']

    f = pd.DataFrame(index=m5.index)

    # Multi-scale returns (match model feature order)
    for bars in [1, 4, 16, 96, 8, 32, 64]:
        f[f'ret_{bars}bar'] = close.pct_change(bars)

    # Range position (multiple horizons)
    for bars, suffix in [(72, '6h'), (144, '12h'), (288, '24h')]:
        rh = close.rolling(bars).max()
        rl = close.rolling(bars).min()
        rng = (rh - rl).replace(0, np.nan)
        f[f'range_pos_{suffix}'] = (close - rl) / rng

    # VWAP deviation (multiple horizons)
    for bars, suffix in [(48, '4h'), (144, '12h'), (288, '24h')]:
        tp = (high + low + close) / 3
        vol = volume.replace(0, 1)
        vwap = (tp * vol).rolling(bars).sum() / vol.rolling(bars).sum()
        f[f'vwap_dev_{suffix}'] = close - vwap

    # ATR (multiple horizons)
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    for bars, suffix in [(36, '3h'), (144, '12h'), (288, '24h')]:
        atr = tr.rolling(bars).mean()
        f[f'atr_{suffix}_pct'] = atr / close

    # Volume ratios
    f['vol_ratio_short'] = volume / volume.rolling(48).mean().replace(0, np.nan)
    f['vol_ratio_long'] = volume / volume.rolling(288).mean().replace(0, np.nan)

    # RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean().replace(0, np.nan)
    f['rsi_14'] = 100 - 100 / (1 + gain / loss)

    # Bollinger position
    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std().replace(0, np.nan)
    f['bb_pos'] = (close - bb_mid) / (2 * bb_std)

    # Volume z-score
    f['vol_zscore'] = (volume - volume.rolling(96).mean()) / volume.rolling(96).std().replace(0, np.nan)

    # Time features
    hour = m5.index.hour + m5.index.minute / 60
    f['cos_hour'] = np.cos(2 * np.pi * hour / 24)
    f['sin_hour'] = np.sin(2 * np.pi * hour / 24)
    f['cos_dow'] = np.cos(2 * np.pi * m5.index.dayofweek / 5)

    # Pullbacks
    for bars, suffix in [(48, '4h'), (144, '12h'), (288, '24h')]:
        rh = high.rolling(bars).max()
        rl = low.rolling(bars).min()
        f[f'pullback_high_{suffix}'] = (rh - close) / close
        f[f'pullback_low_{suffix}'] = (close - rl) / close

    # Spread z-score
    f['spread_zscore'] = (spread - spread.rolling(288).mean()) / spread.rolling(288).std().replace(0, np.nan)

    # Consecutive bars
    f['consec_up'] = (close > close.shift(1)).astype(int)
    f['consec_down'] = (close < close.shift(1)).astype(int)
    for col in ['consec_up', 'consec_down']:
        f[col] = f[col].groupby((f[col] != f[col].shift()).cumsum()).cumsum()

    # Multi-scale consensus
    ret_cols = [c for c in f.columns if c.startswith('ret_') and 'bar' in c]
    f['multi_scale_consensus'] = f[ret_cols].apply(lambda x: (x > 0).sum(), axis=1)

    # Daily aggregates (from daily data)
    daily = m5[['close']].resample('D').last().ffill()
    daily['sma50'] = daily['close'].rolling(50).mean()
    daily['sma100'] = daily['close'].rolling(100).mean()
    daily['ret_5d'] = daily['close'].pct_change(5)

    # Merge daily to M5
    f['daily_sma50'] = daily['sma50'].reindex(m5.index, method='ffill')
    f['daily_sma100'] = daily['sma100'].reindex(m5.index, method='ffill')
    f['daily_ret_5d'] = daily['ret_5d'].reindex(m5.index, method='ffill')

    return f


def main():
    print("=" * 60)
    print("FORENSIC VALIDATION: Him V2 MultiScale")
    print("=" * 60)
    print(f"Model: {MODEL_PATH}")
    print(f"Data: {DATA_PATH}")
    print(f"Locked Config: {LOCKED_CONFIG}")
    print(f"Train: up to {TRAIN_END}")
    print(f"OOS: {OOS_START} onward")
    print()

    # Load data
    print("Loading M5 data...")
    m5 = pd.read_parquet(DATA_PATH)
    m5['time'] = pd.to_datetime(m5['time'])
    m5 = m5.set_index('time')
    validate_ohlcv(m5)
    print(f"  Loaded {len(m5):,} bars ({m5.index[0]} to {m5.index[-1]})")

    # Split train/OOS
    train = m5[m5.index <= TRAIN_END]
    oos = m5[m5.index >= OOS_START]
    print(f"  Train: {len(train):,} bars")
    print(f"  OOS: {len(oos):,} bars")

    # Load model
    print("\nLoading locked model...")
    model = xgb.Booster()
    model.load_model(str(MODEL_PATH))

    # Build features
    print("Building features...")
    features_train = build_multiscale_features(train)
    features_oos = build_multiscale_features(oos)

    # Get predictions
    print("Generating predictions...")
    dmat_train = xgb.DMatrix(features_train.dropna())
    dmat_oos = xgb.DMatrix(features_oos.dropna())

    pred_train = pd.Series(model.predict(dmat_train), index=features_train.dropna().index)
    pred_oos = pd.Series(model.predict(dmat_oos), index=features_oos.dropna().index)

    print(f"  Train predictions: {len(pred_train):,}")
    print(f"  OOS predictions: {len(pred_oos):,}")

    # Compute ATR for both
    print("Computing ATR...")
    def compute_atr(df):
        tr = pd.concat([
            df['high'] - df['low'],
            (df['high'] - df['close'].shift(1)).abs(),
            (df['low'] - df['close'].shift(1)).abs()
        ], axis=1).max(axis=1)
        return tr.rolling(14).mean()

    atr_train = compute_atr(train)
    atr_oos = compute_atr(oos)

    # Configure simulation
    config = SimulationConfig(
        signal_at_bar_i_entry_at_bar_i_plus_n=1,  # Next-bar entry
        hold_bars=LOCKED_CONFIG['hold_bars'],
        stop_loss_atr_mult=LOCKED_CONFIG['stop_atr_mult'],
        take_profit_atr_mult=LOCKED_CONFIG['tp_atr_mult'],
        cost_model=CostModel.xauusd_baseline(),
        position_size_oz=10.0,  # 0.1 lot
    )

    print("\n" + "=" * 60)
    print("TRAIN SET FORENSICS (IN-SAMPLE)")
    print("=" * 60)
    print()

    report_train = run_model_forensics(
        predictions=pred_train,
        ohlcv=train,
        config=config,
        threshold=LOCKED_CONFIG['threshold'],
        atr=atr_train,
        features=features_train,
        output_path=OUTPUT_DIR / "train_forensic_report.json",
    )

    print("\n" + "=" * 60)
    print("OOS FORENSICS (OUT-OF-SAMPLE)")
    print("=" * 60)
    print()

    report_oos = run_model_forensics(
        predictions=pred_oos,
        ohlcv=oos,
        config=config,
        threshold=LOCKED_CONFIG['threshold'],
        atr=atr_oos,
        features=features_oos,
        output_path=OUTPUT_DIR / "oos_forensic_report.json",
    )

    # Compare train vs OOS
    print("\n" + "=" * 60)
    print("TRAIN VS OOS COMPARISON")
    print("=" * 60)

    metrics = ['sharpe', 'total_pnl_net', 'win_rate']
    print(f"\n{'Metric':<20} {'Train':<15} {'OOS':<15} {'Degradation':<15}")
    print("-" * 65)

    for metric in metrics:
        train_val = report_train['baseline']['metrics'][metric]
        oos_val = report_oos['baseline']['metrics'][metric]
        if train_val != 0:
            deg = (oos_val - train_val) / abs(train_val) * 100
            deg_str = f"{deg:+.1f}%"
        else:
            deg_str = "N/A"

        print(f"{metric:<20} {train_val:<15.2f} {oos_val:<15.2f} {deg_str:<15}")

    print()
    print(f"Train Trades: {report_train['baseline']['num_trades']}")
    print(f"OOS Trades: {report_oos['baseline']['num_trades']}")

    # Final verdict
    print("\n" + "=" * 60)
    print("FINAL VERDICT")
    print("=" * 60)
    print(f"Train: {report_train['verdict']}")
    print(f"OOS: {report_oos['verdict']}")

    if "VALIDATED" in report_oos['verdict']:
        print("\n✅ Model PASSES OOS forensic validation")
    elif "WEAK" in report_oos['verdict']:
        print("\n⚠️ Model shows WEAK performance OOS")
    elif "REJECTED" in report_oos['verdict']:
        print("\n❌ Model REJECTED in OOS (fails null tests)")
    else:
        print("\n🚫 Model CONTAMINATED (data validation failed)")

    # Overfitting check
    sharpe_train = report_train['baseline']['metrics']['sharpe']
    sharpe_oos = report_oos['baseline']['metrics']['sharpe']

    if sharpe_train > 0 and sharpe_oos > 0:
        sharpe_ratio = sharpe_oos / sharpe_train
        print(f"\nOOS/Train Sharpe Ratio: {sharpe_ratio:.2f}")
        if sharpe_ratio < 0.5:
            print("  ⚠️ Significant overfitting (OOS < 50% of train)")
        elif sharpe_ratio < 0.8:
            print("  ⚠️ Moderate overfitting (OOS < 80% of train)")
        else:
            print("  ✅ Reasonable generalization")

    print("\n" + "=" * 60)
    print("Reports saved to:")
    print(f"  {OUTPUT_DIR / 'train_forensic_report.json'}")
    print(f"  {OUTPUT_DIR / 'oos_forensic_report.json'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
