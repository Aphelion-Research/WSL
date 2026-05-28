# Optiver Trading Close — Patterns for Dominion

**Repo:** Kaggle competition, stock closing auction prediction  
**Models:** LSTM, ConvNet, LightGBM ensemble  
**Score:** 5.34-5.35 on public LB  
**Date reviewed:** 2026-05-28

---

## Core Architecture

1. **Feature engineering** → raw order book + imbalance ratios + lag diffs + cumsum + deviation from cross-sectional median
2. **Models:**
   - LightGBM (baseline)
   - Dense NN (categorical embedding + numerical → swish + BatchNorm + Dropout)
   - ConvNet (multi-kernel Conv1D + residual + flatten)
3. **Online learning** → after each day, retrain LGB on revealed targets with `keep_training_booster=True`

---

## Transferable Patterns

### 1. Imbalance Features (lines 154-169)
**What:** Pairwise imbalance ratios for bid/ask size/price  
**Function:** `compute_imbalances(df, columns, prefix)`
```python
def compute_imbalances(df, columns, prefix=''):
    for col1, col2 in combinations(columns, 2):
        col1, col2 = sorted([col1, col2])
        total = df[col1] + df[col2]
        imbalance_column_name = f'{col1}_{col2}_imb{prefix}'
        df[imbalance_column_name] = (df[col1] - df[col2]).divide(total, fill_value=np.nan)
    return df
```
**Adapt for XAU/USD:**
- Bid-ask size imbalance (if tick data has bid_size/ask_size)
- Spread pressure: `(bid_size - ask_size) / (bid_size + ask_size)`
- Volume imbalance over rolling window

**Priority:** High (quick win, 1 line per pair)

---

### 2. Rolling Diff Lag Features (lines 154-169)
**What:** Difference between current value and N-bar lagged value  
**Function:** `create_diff_lagged_features_within_date_revised(df, columns_to_lag, numbers_of_lag)`
```python
def create_diff_lagged_features_within_date_revised(df, columns_to_lag, numbers_of_lag):
    df_copy = df.copy()
    new_columns = []
    for lag in numbers_of_lag:
        lagged_df = df.groupby(['stock_id', 'date_id'])[columns_to_lag].shift(periods=lag)
        for column in columns_to_lag:
            new_col_name = f'{column}_diff_lag{lag}'
            new_column = df[column] - lagged_df[column]
            new_columns.append(new_column.rename(new_col_name))
    result_df = pd.concat([df_copy] + new_columns, axis=1)
    return result_df
```
**Adapt:**
- Group by time bucket (e.g., 1-min bars)
- Lags: [1, 2, 3, 5, 10] bars
- Columns: `['close', 'spread', 'volume']`

**Priority:** Medium (overlap with existing lag features, but diff form may help)

---

### 3. Cumulative Sum Features (lines 193-202)
**What:** Cumulative sum of imbalance/volume within trading session  
**Function:** `create_cumsum_features(df, columns_to_compute)`
```python
def create_cumsum_features(df, columns_to_compute):
    df_copy = df.copy()
    grouped = df_copy.groupby(['stock_id', 'date_id'])
    for column in columns_to_compute:
        cumsum_col_name = f'{column}_cumsum'
        df_copy[cumsum_col_name] = grouped[column].cumsum()
    return df_copy
```
**Adapt:**
- Group by trading day (e.g., `date_id`)
- Cumsum: `['volume', 'tick_count', 'spread_change']`
- Reset at each session open

**Priority:** High (intraday accumulation signal)

---

### 4. Deviation from Cross-Sectional Median (lines 219-227)
**What:** How far each stock deviates from median at same timestamp  
**Function:** `create_deviation_within_seconds(df, num_features)`
```python
def create_deviation_within_seconds(df, num_features):
    groupby_cols = ['date_id', 'seconds_in_bucket']
    new_columns = {}
    for feature in num_features:
        grouped_median = df.groupby(groupby_cols)[feature].transform('median')
        deviation_col_name = f'deviation_from_median_{feature}'
        new_columns[deviation_col_name] = df[feature] - grouped_median
    df = pd.concat([df, pd.DataFrame(new_columns)], axis=1)
    return df
```
**Adapt (single instrument):**
- Deviation from rolling intraday median (e.g., last 60 min)
- `(current_close - rolling_median_60m) / rolling_std_60m` → z-score

**Priority:** Low (single instrument, less valuable than multi-stock context)

---

### 5. Global Stock Features (lines 278-306)
**What:** Aggregate stats per stock_id (mean, median, std, quantiles)  
**Adapt:** Not needed (single instrument)

**Priority:** Skip

---

### 6. Target Lag Stats (lines 243-256)
**What:** Mean/std/variance of last N target lags  
**Function:** `calculate_stat_lag(df, num_lags)`
```python
def calculate_stat_lag(df, num_lags):
    lags = [f'lag{i}_target' for i in range(1, num_lags + 1)]
    df['target_mean'] = df[lags].mean(axis=1)
    df['target_std_dev'] = df[lags].std(axis=1)
    df['target_variance'] = df[lags].var(axis=1)
    df['target_median'] = df[lags].median(axis=1)
    df['target_range'] = df[lags].max(axis=1) - df[lags].min(axis=1)
    return df
```
**Adapt:**
- Already have target lags → add rolling moments
- `target_lag1_5_mean`, `target_lag1_5_std`

**Priority:** Medium (simple extension)

---

### 7. Neural Network Architecture (lines 394-423)
**Dense NN:**
- Embedding for categorical (seconds_in_bucket → 10-dim)
- Concatenate with numerical
- Dense layers: [512, 256, 128, 64, 32]
- Activation: swish
- BatchNorm + Dropout(0.4) after each layer
- Loss: MAE
- LR schedule: ExponentialDecay

**Adapt:**
- Port to PyTorch
- Embedding for time-of-day bucket (e.g., 0-23 hours → 16-dim)
- Use swish activation (more stable than ReLU for regression)

**Priority:** Low (already have XGBoost baseline, NN is secondary)

---

### 8. ConvNet RNN Architecture (lines 503-584)
**Multi-kernel Conv1D + residual:**
```python
def apply_conv_layers(input_layer, kernel_sizes, filters=16, do_ratio=0.5):
    conv_outputs = []
    for kernel_size in kernel_sizes:
        conv_layer = Conv1D(filters=filters, kernel_size=kernel_size, activation='relu', padding='same')(input_layer)
        conv_layer = BatchNormalization()(conv_layer)
        conv_layer = Dropout(do_ratio)(conv_layer)
        shortcut = conv_layer
        conv_layer = Conv1D(filters=filters, kernel_size=kernel_size, padding='same')(conv_layer)
        conv_layer = BatchNormalization()(conv_layer)
        conv_layer = Activation('relu')(conv_layer)
        conv_layer = Add()([conv_layer, shortcut])  # residual
        conv_outputs.append(conv_layer)
    concatenated_conv = Concatenate(axis=-1)(conv_outputs)
    flattened_conv_output = Flatten()(concatenated_conv)
    return flattened_conv_output
```
**Adapt:**
- Multi-kernel Conv1D (2, 3, 5) for tick sequences
- Residual connection stabilizes training
- Flatten + concatenate with raw features

**Priority:** Low (heavy, more for deep research)

---

### 9. Online Learning Pattern (lines 868-880)
**LightGBM warm start:**
```python
for lgb_model in lgb_models:
    new_data = lgb.Dataset(daily_online[lgb_features], label=daily_online['target'])
    online_lgb = lgb.train(lgb_params, new_data, init_model=lgb_model, keep_training_booster=True, verbose_eval=1)
    online_lgbs.append(online_lgb)
lgb_models = online_lgbs.copy()
```
**Adapt:**
- XGBoost: `xgb_model = xgb.train(params, dtrain, xgb_model=prev_model)`
- Or: expanding window retrain daily

**Priority:** Medium (useful for walk-forward optimization)

---

## Action Plan

### Phase 1: Imbalance + Cumsum (Quick Wins)
1. Add `compute_imbalances()` for bid-ask spread/volume
2. Add `create_cumsum_features()` for intraday volume/spread accumulation
3. Test on existing XGBoost baseline

**Estimated time:** 2 hours  
**Expected lift:** +1-2% Sharpe

---

### Phase 2: Rolling Diff Lags + Target Stats
1. Add `create_diff_lagged_features_within_date_revised()` for price/spread diffs
2. Add `calculate_stat_lag()` for target lag moments
3. Retrain XGBoost

**Estimated time:** 3 hours  
**Expected lift:** +0.5-1% Sharpe

---

### Phase 3: Dense NN Baseline
1. Port Keras dense NN to PyTorch
2. Embedding for hour-of-day
3. Train on polars-engineered features

**Estimated time:** 1 day  
**Expected lift:** +2-5% Sharpe (ensemble with XGBoost)

---

### Phase 4: Online Learning
1. Add warm-start XGBoost retraining loop
2. Expanding window on walk-forward splits
3. Monitor overfitting

**Estimated time:** 1 day  
**Expected lift:** +1-3% Sharpe (adapts to regime shifts)

---

## Notes

- **Point-in-time safety:** Optiver code uses `.shift()` grouped by `['stock_id', 'date_id']` → safe. Adapt to XAU/USD by grouping on time bucket.
- **No future data:** All features lag by ≥1 bar.
- **Kaggle context:** Closing auction, 55-second window. XAU/USD is continuous, but pattern transfers.
- **Ensemble:** LGB + NN + RNN weighted average. Start with LGB + NN for Dominion.

---

## File Locations

- **Feature engineering:** `optiver-258-nn-modeling-submit.ipynb` cells 3-7
- **Dense NN:** `optiver-258-nn-modeling-submit.ipynb` cell 9
- **ConvNet RNN:** `optiver-258-rnn-modeling-submit.ipynb` cell 11
- **Online learning:** `optiver-258-nn-modeling-submit.ipynb` cell 20 (lines 868-880)

---

## References

- Kaggle competition: [Optiver Trading at the Close](https://www.kaggle.com/competitions/optiver-trading-at-the-close)
- Author: nimashahbazi
- Public LB: 5.3439 (ConvNet), 5.3508 (LSTM)
