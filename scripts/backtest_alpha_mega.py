#!/usr/bin/env python3
"""Backtest HYDRA Alpha Mega model on OOS data with 10k capital."""
import json
import pickle
import numpy as np
import polars as pl
from pathlib import Path

MODEL_PATH = Path("output_hydra_alpha_mega/hydra_mega_model.pkl")
DATASET_PATH = Path("data/hydra_alpha_dataset.parquet")
OUTPUT_DIR = Path("output_backtest_alpha")
OUTPUT_DIR.mkdir(exist_ok=True)

# Trading params
INITIAL_CAPITAL = 10_000
SPREAD_COST = 0.0003  # 30 pips = 0.03%
SLIPPAGE = 0.0001  # 10 pips = 0.01%
RISK_PER_TRADE = 0.01  # 1% of capital per trade
CONF_THRESHOLD = 0.52  # min confidence to trade

def load_model():
    """Load trained mega model."""
    print(f"Loading model: {MODEL_PATH}")
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
    return model

def get_oos_data():
    """Load OOS split (last 20%)."""
    print(f"Loading dataset: {DATASET_PATH}")
    df = pl.read_parquet(DATASET_PATH)

    # Get feature cols (exclude OHLC, labels, time)
    exclude = {"time", "timestamp", "open", "high", "low", "close",
               "tick_volume", "spread", "real_volume"}
    label_cols = {c for c in df.columns if "label" in c.lower()}
    fwd_cols = {c for c in df.columns if "fwd_" in c or "future" in c}
    exclude.update(label_cols)
    exclude.update(fwd_cols)
    feature_cols = [c for c in df.columns if c not in exclude]

    # Filter valid labels
    target_cols = ["label_12b", "label_72b", "label_288b"]
    valid_mask = pl.all_horizontal([pl.col(t).is_not_null() for t in target_cols])
    df_clean = df.filter(valid_mask).sort("time")

    # OOS split (last 20%)
    n = len(df_clean)
    oos_start = int(n * 0.8)
    df_oos = df_clean[oos_start:]

    print(f"OOS split: {len(df_oos):,} bars ({df_oos['time'].min()} → {df_oos['time'].max()})")

    # Fill NaN
    df_oos = df_oos.with_columns([pl.col(c).fill_null(0.0) for c in feature_cols])

    X = df_oos.select(feature_cols).to_numpy().astype(np.float32)
    y = df_oos["label_72b"].to_numpy().astype(np.int32)  # day target
    times = df_oos["time"].to_numpy()

    return X, y, times, feature_cols

def predict_meta(model, X):
    """Get meta predictions from 3-brain ensemble."""
    brains = model["brains"]
    meta_model = model["meta_model"]
    meta_features = model["meta_top_feature_idx"]

    # Brain predictions (LightGBM Booster uses .predict(), not .predict_proba())
    brain_probas = []
    for brain_name in ["scalp", "day", "swing"]:
        brain = brains[brain_name]
        feature_idx = brain["selected_idx"]
        X_brain = X[:, feature_idx]
        proba = brain["model"].predict(X_brain)
        brain_probas.append(proba)

    brain_probas = np.column_stack(brain_probas)

    # Disagreement features
    disagreement = np.column_stack([
        np.std(brain_probas, axis=1),
        np.ptp(brain_probas, axis=1),
        np.abs(brain_probas[:, 0] - brain_probas[:, 1]),
    ])

    # Meta features (top 82 original features)
    X_meta_feats = X[:, meta_features]

    # Stack
    X_meta = np.hstack([brain_probas, disagreement, X_meta_feats])

    # Meta prediction (also LightGBM Booster)
    proba_meta = meta_model.predict(X_meta)

    return proba_meta

def backtest(proba, y, times, initial_capital, conf_threshold):
    """Vectorized backtest with realistic costs."""
    n = len(proba)

    # Trade signals (conf > threshold)
    signals = (proba >= conf_threshold).astype(int)
    signals[proba < (1 - conf_threshold)] = -1  # short if conf < (1-thresh)
    signals[(proba >= (1 - conf_threshold)) & (proba < conf_threshold)] = 0  # no trade

    # Returns (y=1 → price goes up, signal=1 → long)
    returns = np.where(y == 1, 1, -1) * signals  # +1 if correct, -1 if wrong

    # Apply costs
    trade_mask = signals != 0
    costs = np.where(trade_mask, SPREAD_COST + SLIPPAGE, 0.0)
    net_returns = returns * RISK_PER_TRADE - costs

    # Equity curve
    equity = np.zeros(n)
    equity[0] = initial_capital

    for i in range(1, n):
        if trade_mask[i-1]:
            pnl = equity[i-1] * net_returns[i-1]
            equity[i] = equity[i-1] + pnl
        else:
            equity[i] = equity[i-1]

    # Metrics
    trades = np.sum(trade_mask)
    wins = np.sum((returns > 0) & trade_mask)
    win_rate = wins / trades if trades > 0 else 0

    final_equity = equity[-1]
    total_return = (final_equity - initial_capital) / initial_capital

    # Sharpe (annualized, assuming M5 = 288 bars/day)
    daily_returns = []
    for i in range(1, n):
        if equity[i] != equity[i-1]:
            daily_returns.append((equity[i] - equity[i-1]) / equity[i-1])

    if len(daily_returns) > 0:
        sharpe = np.mean(daily_returns) / (np.std(daily_returns) + 1e-8) * np.sqrt(252)
    else:
        sharpe = 0.0

    # Max drawdown
    cummax = np.maximum.accumulate(equity)
    drawdown = (equity - cummax) / cummax
    max_dd = np.min(drawdown)

    return {
        "initial_capital": initial_capital,
        "final_equity": final_equity,
        "total_return_pct": total_return * 100,
        "trades": int(trades),
        "wins": int(wins),
        "win_rate": win_rate,
        "sharpe": sharpe,
        "max_drawdown_pct": max_dd * 100,
        "equity_curve": equity.tolist(),
        "times": [str(t) for t in times],
    }

def main():
    print("\n═══ HYDRA ALPHA MEGA BACKTEST ═══\n")

    # Load
    model = load_model()
    X, y, times, feature_cols = get_oos_data()

    print(f"\nPredicting on {len(X):,} OOS bars...")
    proba = predict_meta(model, X)

    print(f"\nBacktesting with ${INITIAL_CAPITAL:,.0f} capital...")
    print(f"  Confidence threshold: {CONF_THRESHOLD}")
    print(f"  Risk per trade: {RISK_PER_TRADE*100:.1f}%")
    print(f"  Costs: spread={SPREAD_COST*100:.2f}% + slippage={SLIPPAGE*100:.2f}%")

    results = backtest(proba, y, times, INITIAL_CAPITAL, CONF_THRESHOLD)

    # Print
    print("\n═══ RESULTS ═══")
    print(f"  Initial capital: ${results['initial_capital']:,.2f}")
    print(f"  Final equity: ${results['final_equity']:,.2f}")
    print(f"  Total return: {results['total_return_pct']:+.2f}%")
    print(f"  Trades: {results['trades']:,}")
    print(f"  Win rate: {results['win_rate']*100:.2f}%")
    print(f"  Sharpe ratio: {results['sharpe']:.3f}")
    print(f"  Max drawdown: {results['max_drawdown_pct']:.2f}%")

    # Save
    with open(OUTPUT_DIR / "results_alpha_mega.json", "w") as f:
        json.dump(results, f, indent=2)

    np.save(OUTPUT_DIR / "equity_alpha_mega.npy", np.array(results["equity_curve"]))

    print(f"\nSaved: {OUTPUT_DIR}/results_alpha_mega.json")
    print(f"       {OUTPUT_DIR}/equity_alpha_mega.npy")

if __name__ == "__main__":
    main()
