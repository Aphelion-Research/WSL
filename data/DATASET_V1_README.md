# Dominion Dataset v1 — Gold Market ML Training Data

**Generated:** 2026-05-19  
**Version:** 1.0  
**Status:** Production-ready

## Overview

Complete institutional-grade gold market dataset for machine learning. Combines price data, 400+ engineered features, macro indicators, COT positioning, and regime labels into single unified format.

## Files

- **`dataset_v1.parquet`** — Main dataset (3.66 MB, compressed)
- **`dataset_v1.csv`** — CSV version (9.16 MB)
- **`dataset_v1_metadata.json`** — Schema metadata

## Dataset Specifications

| Metric | Value |
|--------|-------|
| **Rows** | 1,256 daily bars |
| **Columns** | 792 total |
| **Date Range** | 2021-05-21 → 2026-05-19 (5 years) |
| **Data Density** | 86.92% (13.08% missing) |
| **Primary Asset** | XAU/USD (gold futures + spot) |

## Column Groups

### 1. OHLCV (5 columns)
Raw price and volume data:
- `timestamp` — Date/time (UTC)
- `open`, `high`, `low`, `close` — Price in USD/oz
- `volume` — Tick volume

### 2. Fused Prices (3 columns)
Kalman-filtered multi-source fusion:
- `fused_price` — Uncertainty-weighted price estimate
- `fused_confidence` — Fusion confidence [0-1]
- `anomaly_flag` — Price anomaly detection (bool)

### 3. Features (379 columns)
Prefix: `feat_*`

Alpha signal features across 7 categories:

**Price (80 features)**
- Returns (1d, 5d, 20d, 50d, 252d)
- Rolling statistics (mean, std, skew, kurt)
- Sharpe ratios, drawdowns
- Hurst exponent, autocorrelation
- ADF stationarity tests
- Fractional differencing

**Microstructure (60 features)**
- Roll spread, Corwin-Schultz spread
- Amihud illiquidity, Kyle's lambda
- VPIN, realized variance
- Bipower variation, jump detection
- Volatility-of-volatility

**Cross-Asset (100 features)**
- Rolling correlation/beta with macro (windows: 5, 10, 20, 50, 100)
- Lead-lag analysis (lags -5 to +5)
- Granger causality
- Partial correlation (controlling for DXY)

**COT (30 features)**
- Net positioning percentile ranks (1y, 2y, 3y windows)
- Speculator sentiment
- Positioning momentum
- Hedger ratios
- Open interest analysis

**Macro (60 features)**
- Real yield (10Y nominal - breakeven inflation)
- Yield curve (slope, curvature)
- DXY momentum
- Fed funds proximity (days to FOMC)
- CPI features
- Real gold price (inflation-adjusted)

**Regime (40 features)**
- HMM tactical regime (trending_up/down, ranging, crisis)
- Microstructure regime (London/NY/Asian/overlap sessions)
- Regime duration
- Historical returns by regime

**Calendar (30 features)**
- Day/week/month/quarter effects
- Month-end, quarter-end
- Options expiry (3rd Friday)
- Seasonal demand (Q4, Ramadan)

### 4. IC Values (379 columns)
Prefix: `ic_*`

Information Coefficient (IC) for each feature — correlation with next-bar return, computed over rolling 252-bar window. Use for feature selection.

### 5. Macro Data (10 columns)
Prefix: `macro_*`

FRED economic series (forward-filled to daily):
- `macro_DGS10` — 10-year Treasury yield
- `macro_DGS2` — 2-year Treasury yield
- `macro_DFII10` — 10-year TIPS (real yield)
- `macro_DTWEXBGS` — Dollar index (DXY proxy)
- `macro_VIXCLS` — VIX volatility index
- `macro_DCOILWTICO` — WTI crude oil
- `macro_CPIAUCSL` — CPI inflation
- `macro_FEDFUNDS` — Fed funds rate
- `macro_T10Y2Y` — 10Y-2Y yield spread
- `macro_T10YIEM` — 10-year breakeven inflation

### 6. COT Positioning (7 columns)
Prefix: `cot_*`

CFTC Commitments of Traders (weekly, forward-filled):
- `cot_commercial_long`, `cot_commercial_short` — Hedger positions
- `cot_noncommercial_long`, `cot_noncommercial_short` — Speculator positions
- `cot_open_interest` — Total open interest
- `cot_net_commercial` — Commercial net (long - short)
- `cot_speculator_sentiment` — % long speculators

### 7. Regime Labels (5 columns)
Prefix: `regime_*`

HMM-detected market regimes:
- `regime_macro_regime` — Macro environment
- `regime_structural_regime` — Long-term structure
- `regime_tactical_regime` — Medium-term trend
- `regime_micro_regime` — Intraday session
- `regime_confidence` — Regime classification confidence

### 8. Target Variables (3 columns)
Forward returns for supervised learning:
- `target_return_1d` — 1-day ahead return
- `target_return_5d` — 5-day ahead return
- `target_return_20d` — 20-day ahead return

## Data Sources

1. **Yahoo Finance** — GC=F gold futures, GLD ETF
2. **MT5/domdata** — XAUUSD real-time quotes
3. **FRED** — 10 macro/economic series
4. **CFTC** — Commitments of Traders reports
5. **Kalman Filter Bank** — Multi-source fusion

## Usage Examples

### Python (pandas)
```python
import pandas as pd

# Load dataset
df = pd.read_parquet('data/dataset_v1.parquet')

# Split train/test (temporal)
train = df[df['timestamp'] < '2025-01-01']
test = df[df['timestamp'] >= '2025-01-01']

# Feature columns
feature_cols = [c for c in df.columns if c.startswith('feat_')]
macro_cols = [c for c in df.columns if c.startswith('macro_')]
cot_cols = [c for c in df.columns if c.startswith('cot_')]

# Select features with high IC
ic_cols = [c.replace('ic_', 'feat_') for c in df.columns 
           if c.startswith('ic_') and df[c].abs().mean() > 0.02]

# Target variable
y = df['target_return_5d']
```

### R
```r
library(arrow)

# Load parquet
df <- read_parquet("data/dataset_v1.parquet")

# Feature selection by IC
ic_threshold <- 0.02
high_ic_features <- names(df)[grepl("^ic_", names(df)) & 
                               abs(colMeans(df[grepl("^ic_", names(df))], na.rm=TRUE)) > ic_threshold]
feature_names <- gsub("^ic_", "feat_", high_ic_features)
```

### PyTorch Dataset
```python
import torch
from torch.utils.data import Dataset

class GoldDataset(Dataset):
    def __init__(self, df, feature_cols, target_col='target_return_5d'):
        self.X = df[feature_cols].fillna(0).values
        self.y = df[target_col].fillna(0).values
        
    def __len__(self):
        return len(self.X)
    
    def __getitem__(self, idx):
        return torch.FloatTensor(self.X[idx]), torch.FloatTensor([self.y[idx]])
```

## Data Quality

- **Missing data:** 13.08% (mostly early-window features)
- **Forward fill:** COT (weekly→daily), macro (variable→daily)
- **Anomaly detection:** 0 anomalies in current dataset
- **Validation:** All sources validated, 16/16 tests pass

## Feature Engineering Pipeline

1. **Raw ingestion** — Multi-source fetch (Yahoo, MT5, FRED, CFTC)
2. **Kalman fusion** — 6-filter bank with dynamic trust scoring
3. **Feature computation** — 400+ features across 7 categories
4. **IC tracking** — Rolling 252-bar correlation with next-bar return
5. **Regime detection** — HMM 4-state tactical regime classifier
6. **Health monitoring** — Staleness, gaps, drift, anomaly detection

## Recommended Workflows

### 1. Feature Selection
```python
# Method A: IC-based
high_ic = df.filter(regex='^ic_').abs().mean().sort_values(ascending=False)
top_features = ['feat_' + c.replace('ic_', '') for c in high_ic.head(50).index]

# Method B: Correlation filter
corr_matrix = df[feature_cols].corr().abs()
upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
to_drop = [c for c in upper.columns if any(upper[c] > 0.95)]
filtered_features = [c for c in feature_cols if c not in to_drop]

# Method C: Regime-conditional
for regime in df['regime_tactical_regime'].unique():
    regime_data = df[df['regime_tactical_regime'] == regime]
    regime_ic = regime_data.filter(regex='^ic_').abs().mean()
    print(f"{regime}: top feature = {regime_ic.idxmax()}")
```

### 2. Train/Val/Test Split
```python
# Temporal split (no data leakage)
train_end = '2024-01-01'
val_end = '2024-07-01'

train = df[df['timestamp'] < train_end]
val = df[(df['timestamp'] >= train_end) & (df['timestamp'] < val_end)]
test = df[df['timestamp'] >= val_end]

print(f"Train: {len(train)} | Val: {len(val)} | Test: {len(test)}")
```

### 3. Regime-Aware Modeling
```python
# Train separate model per regime
from sklearn.ensemble import RandomForestRegressor

models = {}
for regime in df['regime_tactical_regime'].dropna().unique():
    regime_data = df[df['regime_tactical_regime'] == regime]
    X = regime_data[feature_cols].fillna(0)
    y = regime_data['target_return_5d']
    
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)
    models[regime] = model
```

## Changelog

**v1.0 (2026-05-19)**
- Initial release
- 1,256 daily bars (2021-05-21 → 2026-05-19)
- 792 columns (OHLCV + 379 features + 379 ICs + macro + COT + regime + targets)
- 86.92% data density
- Sources: Yahoo, MT5, FRED, CFTC

## License

Proprietary — Blackmark Dominion internal use only.

## Support

Issues/questions: See `AGENT_HANDOFF.md` in repo root.
