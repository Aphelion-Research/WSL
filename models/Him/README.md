# Him

XAU/USD 15-minute scalp model. Predicts whether gold's next 4-hour return
will exceed its trailing average 4-hour return (detrended directional signal).

## Performance (Multi-Period OOS, 2019-2026)

| Threshold | Trades  | Win Rate | Trades/Year |
|-----------|---------|----------|-------------|
| >0.50     | 162,240 | 63.8%    | ~23K        |
| >0.55     | 76,788  | 71.5%    | ~11K        |
| >0.60     | 22,497  | 73.7%    | ~3.2K       |
| >0.65     | 9,858   | 75.6%    | ~1.4K       |
| >0.70     | 4,362   | 79.6%    | ~623        |
| >0.75     | 1,925   | 81.4%    | ~275        |

All p-values < 0.000001. Base rate = 49.8%.

## Usage

```python
import xgboost as xgb

model = xgb.Booster()
model.load_model("models/Him/Him.json")

# Build features for current M15 bar (see config.json for feature list)
# Predict
dmatrix = xgb.DMatrix(features, feature_names=feature_cols)
proba = model.predict(dmatrix)

# Trade logic:
# proba > 0.65 → LONG (expect gold to outperform its trend)
# proba < 0.35 → SHORT (expect gold to underperform its trend)
# else → NO TRADE
```

## Features (26)

Top drivers: ret_96bar (24h momentum), pullback_from_high/low,
range_pos_24h, vwap_dev_24h, cos_hour (session timing).

## Key Details

- Timeframe: M15 bars
- Horizon: 16 bars (4 hours)
- Label: detrended (excess return vs trailing avg)
- Daily overlay: SMA50/100 position shifted 2 days (no lookahead)
- Trained on: 2016-01 to 2025-12
- Validated on: 13 independent 6-month OOS windows

## Files

- `Him.json` — XGBoost model
- `config.json` — feature names, params, gating recommendations
- `validation.json` — full multi-period OOS results
