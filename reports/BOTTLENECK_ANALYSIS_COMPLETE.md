# DOMINION V2 — COMPLETE BOTTLENECK ANALYSIS

**Date:** 2026-05-26  
**Analyst:** Claude Opus 4.6 (automated forensic scan)  
**Repository:** /home/Martin/Dominion  
**Scope:** All Python (13,534 LOC hydra alone), C++ (6,431 LOC kernels + fast_train + backtester), RAGD system (2,550 LOC C++)

---

## EXECUTIVE SUMMARY

### Top 10 Bottlenecks Ranked by Impact

| # | Component | Issue | Est. Speedup | Effort |
|---|-----------|-------|-------------|--------|
| 1 | `features_stationary.py` | O(n×w) Python loops for rolling stats | **50-100x** | 2h |
| 2 | `triple_barrier.py:151-214` | O(n×horizon) scalar loop | **20-30x** | 3h |
| 3 | `cpp/kernels/statistical.cpp:99-132` | rolling_quantile: std::sort per bar | **10-20x** | 1h |
| 4 | `ragd/src/vector_store.cpp:48-64` | O(n) brute-force cosine on every query | **100x+** | 4h |
| 5 | `loader.py:70-92` | 9× redundant sort + 5 DataFrame copies | **5-10x mem** | 1h |
| 6 | `cpp/kernels/rolling.cpp:6-25` | O(n×w) mean/std without sliding window | **3-5x** | 2h |
| 7 | `stacking.py:42-44` | Sequential 12-model × 5-fold training | **4-5x** | 2h |
| 8 | `hydra_288b_fast_train.cpp:718` | malloc per feature in OMP parallel loop | **2-3x** | 30m |
| 9 | `neural.py:72-83` | O(n×seq_len) array copies for LSTM sequences | **10x mem** | 1h |
| 10 | Test suite (162 files) | No parallelization (pytest-xdist missing) | **4-6x** | 30m |

**Total estimated performance gain if all addressed:** 
- Feature engineering: 50-100x faster
- Label generation: 20-30x faster
- C++ kernels: 10-20x faster on quantile, 3-5x on rolling stats
- RAGD queries: 100x+ faster
- Training pipeline: 4-5x faster (parallelization)
- Memory: 5-10x reduction in merge_all

**Quick wins (< 2h each, > 10% gain):** Items 1, 3, 5, 8, 10

---

## SECTION 1: CRITICAL PATH ANALYSIS

### Data Flow Diagram

```
MT5/DuckDB → loader.py (merge_all) → features_stationary.py → features.py (ic_filter)
                                                                      ↓
                                                              triple_barrier.py (labels)
                                                                      ↓
                                                              stacking.py (12 models × 5 folds)
                                                                      ↓
                                                              neural.py (LSTM/TCN/MLP)
                                                                      ↓
                                                              backtester.cpp (simulation)
                                                                      ↓
                                                              hydra_288b_fast_train.cpp (C++ path)
```

### Time Distribution (estimated for 100k bars, 998 features):

| Stage | Current | Optimized | Factor |
|-------|---------|-----------|--------|
| Data Loading (merge_all) | 8-12s | 1-2s | 5x |
| Feature Engineering (stationary) | 60-120s | 1-2s | 50x |
| IC Filter (feature selection) | 30-60s | 5-10s | 6x |
| Label Generation (triple barrier) | 3-5s | 0.1-0.2s | 25x |
| Stacking Training (12×5 folds) | 15-20min | 3-5min | 4x |
| C++ Backtest | 0.5-1s | 0.2-0.5s | 2x |
| C++ Feature Kernels | 5-10s | 0.5-2s | 5x |

---

## SECTION 2: CPU & COMPUTATION BOTTLENECKS

### 2.1 CRITICAL: Python Rolling Statistics — O(n×w) Loops

**File:** `hydra/data/features_stationary.py`

Every rolling computation uses explicit Python `for` loops over n bars with inner numpy slice operations:

**Lines 30-44 — Rolling Z-Score:**
```python
# CURRENT: O(n × w) with numpy overhead per iteration
for i in range(w, len(close)):
    window = close[i-w:i]       # Array slice = copy
    mean = window.mean()         # O(w) numpy call
    std = window.std()           # O(w) numpy call
    if std > 1e-10:
        z = (close[i] - mean) / std
```

Called for windows=[10, 20, 50, 100, 200]. Total: 5 × 100k × avg(76) = 38M numpy operations.

**Lines 81-92 — Realized Volatility:**
```python
for i in range(w, len(close)):
    window = log_ret[i-w+1:i+1]
    rvol[i] = window.std() * np.sqrt(252)
```

**Lines 162-165 — Bollinger Position:**
```python
for i in range(window, len(close)):
    window_data = close[i-window:i]
    bb_mid[i] = window_data.mean()
    bb_std[i] = window_data.std()
```

**Lines 175-189 — Autocorrelation:**
```python
for w in windows:
    for lag in lags:
        for i in range(w + lag, len(close)):
            window = log_ret[i-w:i]
            window_lagged = log_ret[i-w-lag:i-lag]
            autocorr[i] = np.corrcoef(window, window_lagged)[0, 1]
```

This is the worst one: `np.corrcoef` allocates a 2×2 matrix per iteration. With windows=[20,50,100] × lags=[1,5,10] = 9 combinations × 100k bars = 900k `corrcoef` calls.

**Lines 193-219 — Hurst Exponent:**
```python
for i in range(w, len(close)):
    window = log_ret[i-w:i-1]
    mean_ret = window.mean()
    cumsum = (window - mean_ret).cumsum()
    R = cumsum.max() - cumsum.min()
    S = window.std()
```

6 numpy operations per bar per window size.

**OPTIMIZATION — Vectorized Replacement:**

```python
# AFTER: Use pandas rolling (internally Cython, O(n) amortized)
import pandas as pd

def compute_rolling_zscore_fast(close: np.ndarray, windows: list[int]) -> dict[str, np.ndarray]:
    features = {}
    s = pd.Series(close)
    for w in windows:
        rolling = s.rolling(w)
        mean = rolling.mean().values
        std = rolling.std().values
        z = np.where(std > 1e-10, (close - mean) / std, np.nan)
        features[f"rolling_zscore_{w}"] = np.clip(z, -5.0, 5.0).astype(np.float32)
    return features
```

**Expected speedup:** 50-100x (pandas rolling uses Cython with O(n) sliding window internally)

For autocorrelation:
```python
def compute_autocorr_fast(close: np.ndarray, windows: list[int], lags: list[int]) -> dict[str, np.ndarray]:
    features = {}
    log_ret = np.full(len(close), np.nan, dtype=np.float64)
    log_ret[1:] = np.log(close[1:] / close[:-1])
    s = pd.Series(log_ret)
    
    for w in windows:
        for lag in lags:
            # pandas .rolling().corr() is vectorized
            autocorr = s.rolling(w).corr(s.shift(lag)).values.astype(np.float32)
            features[f"autocorr_{w}_lag{lag}"] = autocorr
    return features
```

---

### 2.2 CRITICAL: Triple-Barrier Scalar Loop

**File:** `hydra/labels/triple_barrier.py:151-214`

```python
for t in range(n - self.horizon):          # O(n)
    ...
    for k in range(1, self.horizon + 1):   # O(horizon) nested
        if direction == 1:
            fav = (high[t + k] - entry) / atr[t]
            ...
            if low[t + k] <= stop_px:       # scalar comparison
```

For n=100k, horizon=288: **28.8M scalar iterations** with Python overhead.

**OPTIMIZATION — Vectorized with numpy:**

```python
def label_directional_vectorized(self, high, low, close, atr, spread, direction):
    n = len(close)
    y = np.full(n, np.nan, dtype=np.float32)
    mfe = np.full(n, np.nan, dtype=np.float32)
    mae = np.full(n, np.nan, dtype=np.float32)
    
    # Pre-filter valid bars
    valid = (np.isfinite(atr) & (atr > 0) & 
             (atr / np.where(close > 0, close, 1) >= self.min_atr_pct) &
             (atr >= spread / self.spread_to_atr_min))
    valid_idx = np.where(valid[:n - self.horizon])[0]
    
    # For each valid bar, compute barriers
    entries = close[valid_idx]
    atrs = atr[valid_idx]
    
    if direction == 1:
        stops = entries - self.stop_mult * atrs
        targets = entries + self.target_mult * atrs
    else:
        stops = entries + self.stop_mult * atrs
        targets = entries - self.target_mult * atrs
    
    # Vectorized forward scan using broadcasting
    # Shape: (n_valid, horizon)
    offsets = np.arange(1, self.horizon + 1)
    bar_indices = valid_idx[:, np.newaxis] + offsets[np.newaxis, :]  # (n_valid, horizon)
    
    highs_fwd = high[bar_indices]  # (n_valid, horizon)
    lows_fwd = low[bar_indices]    # (n_valid, horizon)
    
    if direction == 1:
        stop_hit = lows_fwd <= stops[:, np.newaxis]
        target_hit = highs_fwd >= targets[:, np.newaxis]
    else:
        stop_hit = highs_fwd >= stops[:, np.newaxis]
        target_hit = lows_fwd <= targets[:, np.newaxis]
    
    # Apply min_hold_bars mask
    hold_mask = offsets >= self.min_hold_bars
    stop_hit &= hold_mask
    target_hit &= hold_mask
    
    # First hit bar (stop takes priority)
    stop_bars = np.where(stop_hit, offsets, self.horizon + 1).min(axis=1)
    target_bars = np.where(target_hit, offsets, self.horizon + 1).min(axis=1)
    
    # Assign labels
    hit_stop = stop_bars <= target_bars
    hit_target = target_bars < stop_bars
    
    y[valid_idx[hit_stop]] = 0.0
    y[valid_idx[hit_target]] = 1.0
    
    return y, mfe, mae
```

**Expected speedup:** 20-30x (numpy broadcasting replaces nested Python loops)  
**Memory cost:** ~100k × 288 × 8 bytes × 2 arrays ≈ 460MB peak. Chunked version needed for very large datasets.

---

### 2.3 Feature Selection IC Filter

**File:** `hydra/data/features.py:24-54`

```python
def ic_filter(X, y, window, min_abs):
    for j in range(n_feat):                          # 3000 features
        for start in range(0, n_samples - window, window // 2):  # ~200 windows
            rho, _ = spearmanr(x_slice, y_slice)     # O(m log m) per call
```

3000 × 200 × O(500 log 500) = ~1.8B comparison operations.

**OPTIMIZATION:** Use `scipy.stats.spearmanr` on full matrix, or `polars`/`numpy` rank-based correlation:

```python
from scipy.stats import rankdata

def ic_filter_fast(X, y, window, min_abs):
    # Rank once, then use Pearson on ranks (= Spearman)
    y_ranked = rankdata(y)
    X_ranked = np.apply_along_axis(rankdata, 0, X)  # Rank all features at once
    
    # Now compute rolling Pearson (vectorized) between X_ranked and y_ranked
    # ... or use numba @njit for the inner loop
```

---

## SECTION 3: MEMORY & DATA STRUCTURE ISSUES

### 3.1 DataFrame Merge Cascade

**File:** `hydra/data/loader.py:70-92`

```python
df = bars.copy()                                          # Copy 1
df = pd.merge_asof(df.sort_values("ts"), ...)             # Sort + merge 1
df = pd.merge_asof(df.sort_values("ts"), ...)             # Sort + merge 2 (re-sorts!)
df = pd.merge_asof(df.sort_values("ts"), ...)             # Sort + merge 3 (re-sorts!)
df = pd.merge_asof(df.sort_values("ts"), ...)             # Sort + merge 4 (re-sorts!)
```

**Problems:**
1. `bars.copy()` — unnecessary; bars never mutated
2. `df.sort_values("ts")` called 4× on same already-sorted data
3. Each `merge_asof` creates new DataFrame; old one stays in memory until GC
4. 5 DataFrames loaded simultaneously (bars + feats + macro + cot + regimes)

**For 100k rows × 3000 columns at float64:**
- Each DataFrame: 100k × 3000 × 8 = 2.4GB
- Peak memory: 5 DataFrames + 4 intermediate merges ≈ **12-15GB**

**OPTIMIZATION:**

```python
def merge_all_optimized(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    # Load bars (already sorted in SQL)
    df = load_bars(con)
    df["ts"] = pd.to_datetime(df["ts"])
    df.sort_values("ts", inplace=True)  # Sort ONCE
    
    # Merge each source incrementally (they sort themselves once)
    for loader in [load_features, load_macro, load_cot, load_regimes]:
        source = loader(con)
        source["ts"] = pd.to_datetime(source["ts"])
        source.sort_values("ts", inplace=True)
        df = pd.merge_asof(df, source, on="ts", direction="backward")
        del source  # Free immediately
    
    return df.reset_index(drop=True)
```

Or better — do the join in DuckDB:
```python
def merge_all_duckdb(con) -> pd.DataFrame:
    return con.execute("""
        SELECT * FROM gold_master g
        ASOF JOIN features f ON g.timestamp >= f.timestamp
        ASOF JOIN macro_data m ON g.timestamp >= m.timestamp
        ...
    """).df()
```

**Expected improvement:** 5-10x memory reduction, 3-5x speed improvement.

---

### 3.2 LSTM Sequence Generation

**File:** `hydra/models/neural.py:72-83`

```python
def _make_sequences(self, X, y=None):
    seqs = []
    labels = []
    for i in range(seq_len, n):
        seqs.append(X[i - seq_len:i])    # Creates new array copy each time
        labels.append(y[i])
    return np.array(seqs), np.array(labels)  # Stacks all into one array
```

For 100k samples, seq_len=60, 998 features:
- 100k list.append() calls
- Each append copies 60×998 = 59,880 floats
- Final `np.array(seqs)` allocates 100k×60×998×4 = **23.9GB** at float32

**OPTIMIZATION — Stride Tricks (zero-copy):**

```python
def _make_sequences_fast(self, X, y=None):
    from numpy.lib.stride_tricks import sliding_window_view
    seq_len = self.params["seq_len"]
    # Zero-copy view: O(1) memory
    seqs = sliding_window_view(X, window_shape=seq_len, axis=0)[:-1]
    # seqs shape: (n - seq_len, seq_len, n_features) — VIEW, not copy
    labels = y[seq_len:] if y is not None else None
    return seqs, labels
```

**Expected improvement:** 23GB → 0 extra memory (view), 100x faster creation.

---

### 3.3 Stacking Ensemble deepcopy

**File:** `hydra/models/stacking.py:42-44`

```python
import copy
model = copy.deepcopy(model_template)  # Called 12 × 5 = 60 times
```

Each deepcopy of a model template (especially neural nets) is expensive. For sklearn models: ~10-50ms each. For PyTorch models with buffers: ~100-500ms.

**OPTIMIZATION:**

```python
# Models should implement a lightweight clone method
model = model_template.clone()  # Use sklearn's clone() or custom factory

# Or: use model factory pattern
model = model_template.__class__(**model_template.get_params())
```

---

## SECTION 4: I/O & INTEGRATION BOTTLENECKS

### 4.1 DuckDB Pivot Operations in Python

**File:** `hydra/data/loader.py:24-34`

```python
def load_features(con):
    df = con.execute("SELECT timestamp, feature_name, feature_value FROM features").df()
    wide = df.pivot_table(index="ts", columns="feature_name", values="feature_value", aggfunc="first")
```

Loading all features in long format then pivoting in pandas is slow for large tables. With 998 features × 100k timestamps = 99.8M rows loaded, then pivoted.

**OPTIMIZATION:** Pivot in DuckDB (10x faster):

```python
def load_features_fast(con):
    return con.execute("""
        PIVOT features 
        ON feature_name 
        USING first(feature_value) 
        GROUP BY timestamp 
        ORDER BY timestamp
    """).df()
```

### 4.2 RAGD VectorStore — Brute-Force O(n)

**File:** `ragd/src/vector_store.cpp:48-64`

```cpp
std::vector<QueryResult> VectorStore::query(const std::string &text, int limit) const {
    auto q = tf(text);
    std::vector<QueryResult> out;
    for (const auto &kv : documents_) {          // O(n) scan ALL documents
        QueryResult r;
        r.vector_score = cosine(q, kv.second);   // Cosine per document
        out.push_back(std::move(r));
    }
    std::sort(out.begin(), out.end(), ...);       // O(n log n) sort
    if (out.size() > limit) out.resize(limit);
```

For n=10,000 documents, every query does 10,000 cosine comparisons + sort. 

**Additionally:** The `tokenize()` function uses `std::regex` — one of the slowest C++ standard library features:

```cpp
std::vector<std::string> tokenize(const std::string &text) {
    static const std::regex word("[A-Za-z0-9_]+");  // Compiled once (good)
    // But regex iterator is still 10-50x slower than manual tokenization
}
```

**OPTIMIZATION:** Use HNSW index (already in ragd_hnsw/) or at minimum use partial sort:

```cpp
// Use nth_element instead of full sort
std::nth_element(out.begin(), out.begin() + limit, out.end(),
    [](const auto &a, const auto &b) { return a.score > b.score; });
out.resize(limit);
std::sort(out.begin(), out.end(), ...);  // Sort only top-k
```

For tokenizer:
```cpp
std::vector<std::string> tokenize_fast(const std::string &text) {
    std::vector<std::string> out;
    size_t i = 0;
    while (i < text.size()) {
        while (i < text.size() && !std::isalnum(text[i]) && text[i] != '_') ++i;
        size_t start = i;
        while (i < text.size() && (std::isalnum(text[i]) || text[i] == '_')) ++i;
        if (i - start > 1) {
            std::string token = text.substr(start, i - start);
            std::transform(token.begin(), token.end(), token.begin(), ::tolower);
            out.push_back(std::move(token));
        }
    }
    return out;
}
```

### 4.3 Embedding Pipeline — Sequential Batch Processing

**File:** `ragd_embed/pipeline.py`

The embedding pipeline processes chunks sequentially with `time.sleep()` in retry logic. Cache checking is O(n) sequential. No async I/O despite network-bound API calls.

**OPTIMIZATION:** Use `asyncio` + `aiohttp` for concurrent batch embedding:
- Current: 128 texts/batch, sequential batches
- Optimized: 4 concurrent batch requests → 4x throughput

---

## SECTION 5: MACHINE LEARNING PIPELINE ISSUES

### 5.1 Stacking Ensemble — Sequential Model Training

**File:** `hydra/models/stacking.py:37-47`

12 models × 5 folds = 60 sequential train calls. Non-GPU models (XGBoost, LightGBM, RandomForest) release the GIL and can run in parallel.

**OPTIMIZATION:**

```python
from concurrent.futures import ThreadPoolExecutor

def fit_parallel(self, X, y, sample_weight=None):
    n = len(X)
    n_models = len(self.base_models)
    oof = np.zeros((n, n_models), dtype=np.float64)
    kf = KFold(n_splits=self.n_inner_folds, shuffle=False)
    self._fitted_models = [[] for _ in range(n_models)]
    
    def train_one(fold_idx, tr_idx, val_idx, m_idx, model_template):
        model = model_template.__class__(**model_template.get_params())
        model.fit(X[tr_idx], y[tr_idx])
        return m_idx, fold_idx, val_idx, model, model.predict_proba(X[val_idx])
    
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = []
        for fold_idx, (tr_idx, val_idx) in enumerate(kf.split(X)):
            for m_idx, model_template in enumerate(self.base_models):
                futures.append(executor.submit(
                    train_one, fold_idx, tr_idx, val_idx, m_idx, model_template))
        
        for f in futures:
            m_idx, fold_idx, val_idx, model, preds = f.result()
            oof[val_idx, m_idx] = preds
            self._fitted_models[m_idx].append(model)
```

**Expected speedup:** 4-5x with 8 threads (12 models, most GIL-releasing)

### 5.2 Feature Assembly Memory Spike

**File:** `hydra/data/features.py:175-220`

Multiple feature matrices (base + ESN + GAT + causal) are computed independently then horizontally stacked with `np.hstack`. Peak memory = sum of all matrices.

**OPTIMIZATION:** Pre-allocate output matrix, fill columns in-place:

```python
total_cols = n_base + n_esn + n_gat + n_causal
X = np.empty((n_samples, total_cols), dtype=np.float32)
X[:, :n_base] = df[base_cols].values
col_offset = n_base
if FEATURES.add_esn:
    X[:, col_offset:col_offset+n_esn] = esn_features(...)
    col_offset += n_esn
# etc.
```

### 5.3 Walk-Forward Backtesting Redundancy

**File:** `hydra/backtest_9year_final.py` (1516 lines)

This massive file likely contains duplicated logic from `backtest_walkforward.py` (695 lines) and `backtest_walkforward_v2.py` (773 lines). Three versions of similar logic = maintenance burden + potential inconsistency.

---

## SECTION 6: C++ BACKTESTING CORE ANALYSIS

### 6.1 Rolling Kernels — O(n×w) Without Sliding Window

**File:** `cpp/kernels/rolling.cpp:6-52`

Both `rolling_mean` and `rolling_std` use naive O(n×w) algorithm:

```cpp
for (size_t i = window - 1; i < data.size(); ++i) {
    double sum = 0.0;
    int count = 0;
    for (int j = 0; j < window; ++j) {       // O(w) inner loop
        float val = data[i - j];
        if (!std::isnan(val)) {
            sum += val;
            ++count;
        }
    }
}
```

**OPTIMIZATION — Sliding Window (Welford's):**

```cpp
std::vector<float> rolling_mean_fast(const std::vector<float>& data, int window) {
    std::vector<float> result(data.size(), NAN_F);
    double sum = 0.0;
    int count = 0;
    
    // Initialize first window
    for (int j = 0; j < window && j < (int)data.size(); ++j) {
        if (!std::isnan(data[j])) { sum += data[j]; ++count; }
    }
    if (count > 0) result[window - 1] = static_cast<float>(sum / count);
    
    // Slide: O(1) per bar
    for (size_t i = window; i < data.size(); ++i) {
        float old_val = data[i - window];
        float new_val = data[i];
        if (!std::isnan(old_val)) { sum -= old_val; --count; }
        if (!std::isnan(new_val)) { sum += new_val; ++count; }
        result[i] = count > 0 ? static_cast<float>(sum / count) : NAN_F;
    }
    return result;
}
```

For window=50, this is **50x fewer arithmetic operations**.

### 6.2 CRITICAL: Rolling Quantile with std::sort

**File:** `cpp/kernels/statistical.cpp:99-132`

```cpp
for (size_t i = window - 1; i < data.size(); ++i) {
    std::vector<float> vals;
    vals.reserve(window);
    for (int j = 0; j < window; ++j) {
        vals.push_back(data[i - j]);
    }
    std::sort(vals.begin(), vals.end());  // O(w log w) PER BAR
}
```

For 100k bars, window=50: 100k × (50 log 50) ≈ 28M comparisons.

**OPTIMIZATION 1 — nth_element (sufficient for single quantile):**

```cpp
std::nth_element(vals.begin(), vals.begin() + rank, vals.end());
result[i] = vals[rank];
```

O(w) average instead of O(w log w).

**OPTIMIZATION 2 — Sorted sliding window (amortized O(log w)):**

```cpp
// Use order-statistic tree or multiset for O(log w) insert/remove/query
#include <ext/pb_ds/assoc_container.hpp>
// ... or simpler: maintain sorted deque with binary insertion
```

**Expected speedup:** 10-20x with nth_element alone.

### 6.3 Rolling Autocorrelation — Allocation + Reverse

**File:** `cpp/kernels/statistical.cpp:54-96`

```cpp
for (size_t i = window - 1; i < data.size(); ++i) {
    std::vector<double> vals;          // HEAP ALLOCATION per bar
    vals.reserve(window);
    // ... fill ...
    std::reverse(vals.begin(), vals.end());  // UNNECESSARY with index math
    // ... compute correlation ...
}
```

**OPTIMIZATION:** Pre-allocate buffer, remove reverse:

```cpp
std::vector<float> rolling_autocorr_fast(const std::vector<float>& data, int window, int lag) {
    std::vector<float> result(data.size(), NAN_F);
    // Single pre-allocated buffer
    std::vector<double> buf(window);
    
    for (size_t i = window - 1; i < data.size(); ++i) {
        // Fill in chronological order directly (reverse index)
        int count = 0;
        for (int j = window - 1; j >= 0; --j) {
            float val = data[i - j];
            if (!std::isnan(val)) buf[count++] = val;
        }
        // ... compute on buf[0..count] ...
    }
    return result;
}
```

### 6.4 Feature Scoring — Cache Miss Pattern + malloc

**File:** `cpp/hydra_288b_fast_train.cpp:715-720`

```cpp
#pragma omp parallel for schedule(dynamic, 8)
for (int j = 0; j < n_total_features; ++j) {
    vector<double> feat(n_samples);          // MALLOC per feature per thread
    for (int i = 0; i < n_samples; ++i) {
        feat[i] = X[i][j];                   // COLUMN access on row-major = CACHE MISS
    }
```

**Two problems:**
1. `vector<double> feat(n_samples)` = malloc/free × n_features in hot parallel loop
2. `X[i][j]` is column access on row-major data = L1 cache miss every 8 accesses

**OPTIMIZATION:**

```cpp
// 1. Thread-local pre-allocated buffer
thread_local std::vector<double> feat_buffer;

#pragma omp parallel for schedule(dynamic, 8)
for (int j = 0; j < n_total_features; ++j) {
    if (feat_buffer.size() < n_samples) feat_buffer.resize(n_samples);
    
    // 2. Transpose X before scoring (or maintain column-major copy)
    for (int i = 0; i < n_samples; ++i) {
        feat_buffer[i] = X_transposed[j][i];  // Sequential access = no cache miss
    }
    // ... score feat_buffer ...
}
```

**Expected speedup:** 2-3x (eliminates malloc + cache misses)

### 6.5 Backtester — Branch Prediction

**File:** `hydra/backtest/cpp/backtester.cpp:78-84`

```cpp
if (direction == 1) {
    if (low[t] <= stop_px) { ... }
    else if (high[t] >= target_px) { ... }
} else {
    if (high[t] >= stop_px) { ... }
    else if (low[t] <= target_px) { ... }
}
```

Direction changes per-trade (not per-bar), so branch predictor handles this well. **Low priority** — already fast at 162M bars/sec.

### 6.6 Missing Compiler Optimizations

**File:** `cpp/CMakeLists.txt`

Currently: `-O3 -march=native -ffast-math`

**Missing:**
```cmake
# Add Link-Time Optimization (cross-TU inlining)
set(CMAKE_INTERPROCEDURAL_OPTIMIZATION TRUE)

# Profile-Guided Optimization (2-pass build)
# Pass 1: -fprofile-generate
# Pass 2: -fprofile-use
```

LTO alone typically gives 5-15% improvement on numerical code.

---

## SECTION 7: SYSTEM ARCHITECTURE ISSUES

### 7.1 Python ↔ C++ Boundary

Pybind11 marshaling for large arrays is efficient (numpy buffer protocol), but the feature kernels return `std::vector<float>` which requires a copy back to Python. Consider returning numpy arrays directly via buffer protocol.

### 7.2 RAGD Architecture — Dual Index Not Leveraged

The system has `ragd_hnsw/` (proper HNSW index) but `ragd/src/vector_store.cpp` still uses brute-force. The HNSW module exists but may not be wired to the main daemon for all query paths.

### 7.3 No Shared Feature Cache

Features computed in `features_stationary.py` are recomputed every training run. No disk cache of computed features keyed by (data_hash, feature_config_hash).

**OPTIMIZATION:** DuckDB materialized views or Parquet feature store:

```python
import hashlib

def get_or_compute_features(close, feature_config):
    key = hashlib.md5(close.tobytes() + str(feature_config).encode()).hexdigest()
    cache_path = f"data/feature_fabric/{key}.parquet"
    if Path(cache_path).exists():
        return pl.read_parquet(cache_path)
    features = compute_all_features(close, feature_config)
    features.write_parquet(cache_path)
    return features
```

---

## SECTION 8: TESTING & DEVELOPMENT BOTTLENECKS

### 8.1 Test Suite — No Parallelization

**Config:** `pytest.ini` has no `-n auto` (pytest-xdist not installed)

162 test files run sequentially. Estimated total: 5-10 minutes.

**Fix (30 minutes):**
```bash
pip install pytest-xdist
# Add to pytest.ini:
# addopts = --import-mode=importlib -m "not integration" -n auto
```

**Expected speedup:** 4-6x on 8-core machine.

### 8.2 Markers Underutilized

3 markers defined, only 1 actively used. ~20+ integration tests not marked, running in fast feedback loops.

### 8.3 No Performance Regression Tests

No benchmark suite that catches regressions when feature engineering or kernel code changes. Could use `pytest-benchmark`:

```python
def test_rolling_zscore_performance(benchmark):
    close = np.random.randn(100_000).astype(np.float32)
    benchmark(compute_rolling_zscore, close, [20, 50])
```

---

## SECTION 9: DETAILED ACTION ITEMS

### Item 1: Vectorize features_stationary.py

| Field | Value |
|-------|-------|
| **File** | `hydra/data/features_stationary.py` |
| **Functions** | `compute_rolling_zscore`, `compute_realized_vol`, `compute_bollinger_position`, `compute_autocorr`, `compute_hurst`, `compute_sharpe_rolling`, `compute_drawdown_pct` |
| **Root Cause** | Python `for` loops with per-iteration numpy calls |
| **Solution** | Replace with `pd.Series.rolling()` or `bottleneck` library |
| **Impact** | 50-100x faster feature engineering |
| **Effort** | 2 hours |
| **Risk** | Low — numerical equivalence easy to verify |
| **Dependencies** | None (pandas already imported) |

### Item 2: Vectorize triple_barrier labeling

| Field | Value |
|-------|-------|
| **File** | `hydra/labels/triple_barrier.py:151-214` |
| **Function** | `label_directional` |
| **Root Cause** | Nested Python for-loop over n × horizon |
| **Solution** | numpy broadcasting + argmin for first-hit detection |
| **Impact** | 20-30x faster label generation |
| **Effort** | 3 hours |
| **Risk** | Medium — must verify exact label equivalence at edge cases |
| **Dependencies** | May need chunking for large datasets (memory) |

### Item 3: Fix C++ rolling_quantile

| Field | Value |
|-------|-------|
| **File** | `cpp/kernels/statistical.cpp:99-132` |
| **Function** | `rolling_quantile` |
| **Root Cause** | std::sort O(w log w) per bar |
| **Solution** | std::nth_element O(w) average |
| **Impact** | 10-20x faster |
| **Effort** | 1 hour |
| **Risk** | Very low — drop-in replacement |
| **Dependencies** | None |

### Item 4: Fix RAGD VectorStore brute-force

| Field | Value |
|-------|-------|
| **File** | `ragd/src/vector_store.cpp:48-64` |
| **Function** | `VectorStore::query` |
| **Root Cause** | Linear scan + full sort of all documents |
| **Solution** | Wire HNSW index (already exists in ragd_hnsw/), or use partial_sort |
| **Impact** | 100x+ for large document sets |
| **Effort** | 4 hours (to wire existing HNSW) |
| **Risk** | Low (HNSW already tested separately) |
| **Dependencies** | ragd_hnsw module |

### Item 5: Fix loader.py merge cascade

| Field | Value |
|-------|-------|
| **File** | `hydra/data/loader.py:70-92` |
| **Function** | `merge_all` |
| **Root Cause** | 9× redundant sorts, unnecessary copies, no column pruning |
| **Solution** | Sort once, delete intermediates, or push join to DuckDB |
| **Impact** | 5-10x memory, 3-5x speed |
| **Effort** | 1 hour |
| **Risk** | Very low |
| **Dependencies** | None |

### Item 6: C++ sliding window for rolling_mean/std

| Field | Value |
|-------|-------|
| **File** | `cpp/kernels/rolling.cpp:6-52` |
| **Functions** | `rolling_mean`, `rolling_std` |
| **Root Cause** | Recomputes sum from scratch each bar |
| **Solution** | Sliding window with add/remove |
| **Impact** | 3-5x (proportional to window size) |
| **Effort** | 2 hours |
| **Risk** | Low — well-known algorithm, needs NaN handling |
| **Dependencies** | None |

### Item 7: Parallelize stacking ensemble

| Field | Value |
|-------|-------|
| **File** | `hydra/models/stacking.py:37-47` |
| **Function** | `StackingEnsemble.fit` |
| **Root Cause** | Sequential training of 12 models × 5 folds |
| **Solution** | ThreadPoolExecutor for GIL-releasing models |
| **Impact** | 4-5x training speed |
| **Effort** | 2 hours |
| **Risk** | Low — models are independent per fold |
| **Dependencies** | None |

### Item 8: Thread-local buffers in C++ feature scoring

| Field | Value |
|-------|-------|
| **File** | `cpp/hydra_288b_fast_train.cpp:718` |
| **Function** | `score_all_features` |
| **Root Cause** | malloc/free per feature in OMP loop |
| **Solution** | `thread_local` pre-allocated buffer |
| **Impact** | 2-3x faster scoring |
| **Effort** | 30 minutes |
| **Risk** | Very low |
| **Dependencies** | None |

### Item 9: LSTM stride tricks

| Field | Value |
|-------|-------|
| **File** | `hydra/models/neural.py:72-83` |
| **Function** | `_make_sequences` |
| **Root Cause** | N array copies + final concatenation |
| **Solution** | `numpy.lib.stride_tricks.sliding_window_view` |
| **Impact** | 23GB → 0 extra memory, 100x creation speed |
| **Effort** | 1 hour |
| **Risk** | Low — must ensure contiguous copy for GPU transfer |
| **Dependencies** | numpy >= 1.20 |

### Item 10: Test parallelization

| Field | Value |
|-------|-------|
| **File** | `pytest.ini` |
| **Root Cause** | No pytest-xdist, tests run serially |
| **Solution** | Install pytest-xdist, add `-n auto` |
| **Impact** | 4-6x faster test suite |
| **Effort** | 30 minutes |
| **Risk** | Low — may need fixture isolation fixes |
| **Dependencies** | pytest-xdist package |

---

## SECTION 10: IMPLEMENTATION ROADMAP

### Phase 1: Quick Wins (< 5 hours total, immediate)

| # | Task | Time | Impact |
|---|------|------|--------|
| 1 | Fix `rolling_quantile` → nth_element | 1h | 10-20x kernel |
| 2 | Thread-local buffers in feature scoring | 30m | 2-3x scoring |
| 3 | Fix `loader.py` merge cascade | 1h | 5-10x memory |
| 4 | Install pytest-xdist, add -n auto | 30m | 4-6x tests |
| 5 | LSTM stride_tricks | 1h | 23GB memory saved |
| 6 | Add LTO to CMakeLists.txt | 15m | 5-15% all C++ |

### Phase 2: High-Impact Improvements (1-2 weeks)

| # | Task | Time | Impact |
|---|------|------|--------|
| 7 | Vectorize features_stationary.py (all functions) | 4h | 50-100x features |
| 8 | Vectorize triple_barrier labeling | 3h | 20-30x labels |
| 9 | C++ sliding window for rolling_mean/std | 2h | 3-5x kernels |
| 10 | Parallelize stacking ensemble | 2h | 4-5x training |
| 11 | Vectorize IC filter with numba | 3h | 6x selection |
| 12 | DuckDB PIVOT for load_features | 1h | 3-5x loading |

### Phase 3: Architectural Changes (2-4 weeks)

| # | Task | Time | Impact |
|---|------|------|--------|
| 13 | Wire HNSW to RAGD daemon (replace brute-force) | 4h | 100x+ queries |
| 14 | Feature cache (Parquet store keyed by config hash) | 8h | Skip recompute |
| 15 | SIMD kernels for rolling operations (AVX2) | 16h | 4-8x all kernels |
| 16 | Consolidate backtest_{3year,9year,walkforward*} | 8h | Maintainability |
| 17 | Async embedding pipeline | 4h | 4x embedding |
| 18 | C++ feature matrix transpose for cache efficiency | 2h | 2-3x scoring |

### Phase 4: Long-Term Strategic (1+ month)

| # | Task | Time | Impact |
|---|------|------|--------|
| 19 | GPU-accelerated feature kernels (CUDA) | 40h | 10-50x features |
| 20 | Online/incremental feature computation | 24h | Real-time ready |
| 21 | Distributed training (Ray/Dask) | 40h | Scale to larger datasets |
| 22 | Profile-Guided Optimization for C++ | 4h | 10-20% all C++ |
| 23 | Custom allocator for kernel operations | 16h | Reduce GC pressure |

---

## SECTION 11: MONITORING & VALIDATION

### Key Metrics to Track

| Metric | Baseline (estimated) | Target | Tool |
|--------|---------------------|--------|------|
| Feature engineering time (100k bars) | 60-120s | 1-2s | time.time() |
| Triple-barrier labeling (100k bars) | 3-5s | 0.1-0.2s | time.time() |
| C++ rolling_quantile (100k, w=50) | 500ms | 25-50ms | chrono |
| merge_all peak memory | 12-15GB | 1-2GB | tracemalloc |
| Stacking training (12 models) | 15-20min | 3-5min | time.time() |
| RAGD query (10k docs) | 50-100ms | 0.5-1ms | chrono |
| Test suite total | 5-10min | 1-2min | pytest --durations |
| C++ feature scoring (1000 features) | 2-3s | 0.8-1s | ScopedTimer |

### Profiling Methodology

```python
# Python: use line_profiler for hot functions
# pip install line_profiler
@profile
def compute_rolling_zscore(close, windows):
    ...

# C++: use perf or Intel VTune
# perf stat -e cache-misses,branch-misses ./hydra_features_test

# Memory: tracemalloc
import tracemalloc
tracemalloc.start()
result = merge_all(con)
snapshot = tracemalloc.take_snapshot()
top = snapshot.statistics('lineno')[:10]
```

### Regression Testing

```python
# Add to CI (when CI exists):
def test_feature_engineering_speed():
    close = np.random.randn(100_000).astype(np.float32)
    start = time.time()
    compute_all_stationary_features(close, ...)
    elapsed = time.time() - start
    assert elapsed < 5.0, f"Feature engineering took {elapsed:.1f}s (max 5s)"
```

---

## APPENDIX A: COMPARATIVE ANALYSIS

### How Industry Leaders Handle These Problems

| Problem | Dominion (Current) | Citadel/Two Sigma Approach |
|---------|-------------------|---------------------------|
| Rolling statistics | Python for-loops | C++/Rust SIMD kernels, Intel MKL |
| Feature computation | Recompute every run | Incremental feature store (Feast/Tecton) |
| Sequence generation | Array copies | Memory-mapped views, zero-copy |
| Ensemble training | Sequential Python | Distributed (Ray), hardware-pinned |
| Vector search | Brute-force O(n) | FAISS/ScaNN, GPU-accelerated |
| Data loading | pandas merge_asof | Arrow Flight, zero-copy IPC |
| Backtesting | 162M bars/sec (C++) | 500M+ bars/sec (FPGA/GPU) |

### Dominion's Competitive Position

**Strengths:**
- C++ backtester is already fast (162M bars/sec)
- Correct architecture (SoA, OpenMP, pybind11)
- DuckDB for analytics (good choice)
- Clean separation of concerns

**Gaps (vs. institutional):**
- Python feature engineering is orders of magnitude slower than needed
- No feature caching/materialization
- RAGD vector search not using its own HNSW module
- Test infrastructure immature (no CI, no parallelization)

---

## APPENDIX B: CODE COMPLEXITY METRICS

| File | Lines | Cyclomatic Complexity | Hot Loops | Priority |
|------|-------|-----------------------|-----------|----------|
| `features_stationary.py` | 502 | High (7 nested loops) | 7 | CRITICAL |
| `triple_barrier.py` | 371 | High (nested conditional) | 1 | CRITICAL |
| `hydra_288b_fast_train.cpp` | 5644 | Very High | 10+ | MEDIUM |
| `backtest_9year_final.py` | 1516 | High | Unknown | LOW |
| `rolling.cpp` | 243 | Medium (4 kernels) | 4 | HIGH |
| `statistical.cpp` | 134 | Medium (3 kernels) | 3 | CRITICAL |
| `stacking.py` | 78 | Low | 2 | HIGH |
| `loader.py` | 92 | Low | 0 | HIGH |

---

## APPENDIX C: FULL QUICK WINS CHECKLIST

- [ ] `statistical.cpp:117` — Replace `std::sort` with `std::nth_element`
- [ ] `hydra_288b_fast_train.cpp:718` — Add `thread_local` buffer
- [ ] `loader.py:83` — Remove `.copy()`, sort once
- [ ] `loader.py:84-91` — Remove redundant `.sort_values("ts")`
- [ ] `pytest.ini` — Add `pip install pytest-xdist` + `-n auto`
- [ ] `neural.py:72-83` — Use `sliding_window_view`
- [ ] `CMakeLists.txt` — Add `set(CMAKE_INTERPROCEDURAL_OPTIMIZATION TRUE)`
- [ ] `statistical.cpp:62-63` — Pre-allocate buffer outside loop
- [ ] `rolling.cpp:13-18` — Convert to sliding window (mean)
- [ ] `rolling.cpp:35-41` — Convert to Welford's (std)

---

*End of analysis. Total components scanned: 60+ Python files, 8 C++ source files, 4 config files, 162 test files. Generated 2026-05-26.*
