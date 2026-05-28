"""Him Profit Max Live TUI - Manual Trading Signals

Shows realtime buy/sell signals from Him Profit Max model.
You execute trades manually.

Requirements:
    pip install rich

Usage:
    python scripts/him_live_tui.py
"""
import sys
import time
import subprocess
import json
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
import xgboost as xgb
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.console import Console
from rich import box

sys.path.insert(0, str(Path(__file__).parent.parent))

console = Console()

# Load model
MODEL_PATH = "output_him_v2/him_profit_max.json"
THRESHOLD = 0.65
LOOKBACK_BARS = 300  # Need 288 for daily features

print(f"Loading model: {MODEL_PATH}")
model = xgb.Booster()
model.load_model(MODEL_PATH)
print("Model loaded ✓")

def get_latest_m5_bars(count=LOOKBACK_BARS):
    """Get latest M5 bars from domdata."""
    # domdata gives M1, need 5x bars for M5 resample
    cmd = f"domdata xaurates --count {count * 5}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"domdata failed: {result.stderr}")

    # Parse JSON array
    bars = json.loads(result.stdout)

    if len(bars) == 0:
        raise RuntimeError("No data from domdata")

    # Convert to DataFrame
    df = pd.DataFrame(bars)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df = df.set_index('time')

    # Resample to M5
    df = df.resample('5min').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'tick_volume': 'sum',
        'spread': 'mean',
    }).dropna()

    return df.tail(count)

def build_features(df):
    """Build Him V2 features."""
    close = df['close']
    high = df['high']
    low = df['low']
    volume = df['tick_volume']
    spread = df['spread']

    f = pd.DataFrame(index=df.index)

    # Returns
    for bars in [1, 4, 16, 96, 8, 32, 64]:
        f[f'ret_{bars}bar'] = close.pct_change(bars)

    # Range position
    for bars, suffix in [(72, '6h'), (144, '12h'), (288, '24h')]:
        rh = close.rolling(bars).max()
        rl = close.rolling(bars).min()
        rng = (rh - rl).replace(0, np.nan)
        f[f'range_pos_{suffix}'] = (close - rl) / rng

    # VWAP deviation
    for bars, suffix in [(48, '4h'), (144, '12h'), (288, '24h')]:
        tp = (high + low + close) / 3
        vol = volume.replace(0, 1)
        vwap = (tp * vol).rolling(bars).sum() / vol.rolling(bars).sum()
        f[f'vwap_dev_{suffix}'] = close - vwap

    # ATR
    tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
    for bars, suffix in [(36, '3h'), (144, '12h'), (288, '24h')]:
        atr = tr.rolling(bars).mean()
        f[f'atr_{suffix}_pct'] = atr / close

    # Volume
    f['vol_ratio_short'] = volume / volume.rolling(48).mean().replace(0, np.nan)
    f['vol_ratio_long'] = volume / volume.rolling(288).mean().replace(0, np.nan)

    # RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean().replace(0, np.nan)
    f['rsi_14'] = 100 - 100 / (1 + gain / loss)

    # Bollinger
    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std().replace(0, np.nan)
    f['bb_pos'] = (close - bb_mid) / (2 * bb_std)

    # Volume z-score
    f['vol_zscore'] = (volume - volume.rolling(96).mean()) / volume.rolling(96).std().replace(0, np.nan)

    # Session
    hour = df.index.hour + df.index.minute / 60
    f['cos_hour'] = np.cos(2 * np.pi * hour / 24)
    f['sin_hour'] = np.sin(2 * np.pi * hour / 24)
    f['cos_dow'] = np.cos(2 * np.pi * df.index.dayofweek / 5)

    # Pullback
    for bars, suffix in [(48, '4h'), (144, '12h'), (288, '24h')]:
        rh = high.rolling(bars).max()
        rl = low.rolling(bars).min()
        f[f'pullback_high_{suffix}'] = (rh - close) / close
        f[f'pullback_low_{suffix}'] = (close - rl) / close

    # Spread z-score
    f['spread_zscore'] = (spread - spread.rolling(288).mean()) / spread.rolling(288).std().replace(0, np.nan)

    # Consecutive
    f['consec_up'] = (close > close.shift(1)).astype(int)
    f['consec_down'] = (close < close.shift(1)).astype(int)
    for col in ['consec_up', 'consec_down']:
        f[col] = f[col].groupby((f[col] != f[col].shift()).cumsum()).cumsum()

    # Multi-scale consensus
    ret_cols = [c for c in f.columns if c.startswith('ret_') and 'bar' in c]
    f['multi_scale_consensus'] = f[ret_cols].apply(lambda x: (x > 0).sum(), axis=1)

    # Daily features (fill with dummy values - need 100 days for real data)
    daily = df[['close']].resample('D').last().ffill()
    daily['sma50'] = daily['close'].rolling(50).mean()
    daily['sma100'] = daily['close'].rolling(100).mean()
    daily['ret_5d'] = daily['close'].pct_change(5)
    f['daily_sma50'] = daily['sma50'].reindex(df.index, method='ffill').fillna(close.iloc[-1])
    f['daily_sma100'] = daily['sma100'].reindex(df.index, method='ffill').fillna(close.iloc[-1])
    f['daily_ret_5d'] = daily['ret_5d'].reindex(df.index, method='ffill').fillna(0.0)

    # ATR for stops
    atr_14 = tr.rolling(14).mean()

    return f, atr_14

def predict_signal(df):
    """Build features and predict."""
    features, atr = build_features(df)

    # Get last bar features
    X = features.iloc[-1:]
    if X.isna().any().any():
        return None, None, None

    # Predict
    dmat = xgb.DMatrix(X)
    pred = model.predict(dmat)[0]

    # Signal
    signal = "BUY" if pred > THRESHOLD else "WAIT"

    # Stop/TP levels
    current_price = df['close'].iloc[-1]
    current_atr = atr.iloc[-1]

    stop_loss = current_price - 1.5 * current_atr
    take_profit = current_price + 3.0 * current_atr

    return {
        'signal': signal,
        'confidence': pred,
        'price': current_price,
        'atr': current_atr,
        'stop_loss': stop_loss,
        'take_profit': take_profit,
        'time': df.index[-1],
    }, df, atr

def create_display(signal_data, bars, history):
    """Create TUI display."""
    layout = Layout()

    if signal_data is None:
        return Panel("[yellow]Waiting for data...[/yellow]")

    # Current signal panel
    signal = signal_data['signal']
    conf = signal_data['confidence']
    price = signal_data['price']
    atr = signal_data['atr']
    sl = signal_data['stop_loss']
    tp = signal_data['take_profit']
    ts = signal_data['time']

    # Color
    if signal == "BUY":
        color = "green"
        icon = "🟢"
    else:
        color = "dim"
        icon = "⚪"

    # Signal table
    signal_table = Table(show_header=False, box=box.ROUNDED, expand=True)
    signal_table.add_column("", style="bold")
    signal_table.add_column("", justify="right")

    signal_table.add_row("Signal", f"[{color}]{icon} {signal}[/{color}]")
    signal_table.add_row("Confidence", f"{conf:.3f} (threshold: {THRESHOLD})")
    signal_table.add_row("Price", f"${price:.2f}")
    signal_table.add_row("ATR (14)", f"${atr:.2f}")
    signal_table.add_row("Stop Loss", f"[red]${sl:.2f}[/red] ({sl - price:.2f})")
    signal_table.add_row("Take Profit", f"[green]${tp:.2f}[/green] (+{tp - price:.2f})")
    signal_table.add_row("Time", str(ts))

    signal_panel = Panel(signal_table, title="[bold]Him Profit Max Live Signal[/bold]", border_style=color)

    # Recent bars table
    bars_table = Table(box=box.SIMPLE, expand=True)
    bars_table.add_column("Time", style="dim")
    bars_table.add_column("Open", justify="right")
    bars_table.add_column("High", justify="right", style="green")
    bars_table.add_column("Low", justify="right", style="red")
    bars_table.add_column("Close", justify="right", style="bold")
    bars_table.add_column("Volume", justify="right")

    for idx in bars.index[-5:]:
        bar = bars.loc[idx]
        bars_table.add_row(
            idx.strftime("%H:%M"),
            f"{bar['open']:.2f}",
            f"{bar['high']:.2f}",
            f"{bar['low']:.2f}",
            f"{bar['close']:.2f}",
            f"{int(bar['tick_volume'])}",
        )

    bars_panel = Panel(bars_table, title="[bold]Recent M5 Bars[/bold]")

    # History table
    history_table = Table(box=box.SIMPLE, expand=True)
    history_table.add_column("Time", style="dim")
    history_table.add_column("Signal", justify="center")
    history_table.add_column("Conf", justify="right")
    history_table.add_column("Price", justify="right")

    for h in history[-10:]:
        sig_color = "green" if h['signal'] == "BUY" else "dim"
        history_table.add_row(
            h['time'].strftime("%m-%d %H:%M"),
            f"[{sig_color}]{h['signal']}[/{sig_color}]",
            f"{h['confidence']:.3f}",
            f"${h['price']:.2f}",
        )

    history_panel = Panel(history_table, title="[bold]Signal History (last 10)[/bold]")

    # Layout
    layout.split_column(
        Layout(signal_panel, size=10),
        Layout(bars_panel, size=9),
        Layout(history_panel),
    )

    return layout

def main():
    """Main TUI loop."""
    console.print("[bold green]Him Profit Max Live TUI[/bold green]")
    console.print(f"Model: {MODEL_PATH}")
    console.print(f"Threshold: {THRESHOLD}")
    console.print(f"Updating every 60 seconds...\n")

    history = []

    with Live(console=console, refresh_per_second=1) as live:
        while True:
            try:
                # Get latest data
                bars = get_latest_m5_bars(LOOKBACK_BARS)

                # Predict
                signal_data, bars, atr = predict_signal(bars)

                # Add to history
                if signal_data and (not history or signal_data['time'] != history[-1]['time']):
                    history.append(signal_data)

                # Update display
                display = create_display(signal_data, bars, history)
                live.update(display)

                # Wait 60s before next update
                time.sleep(60)

            except KeyboardInterrupt:
                console.print("\n[yellow]Shutting down...[/yellow]")
                break
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                time.sleep(10)

if __name__ == "__main__":
    main()
