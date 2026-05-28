---
doc_type: workflow
system: Dominion
audience: [owner, ai_agent]
status: current
last_updated: 2026-05-20
tags: [claude-code, workflows, skills, prompts]
---

# Claude Code Workflows for Dominion/HYDRA

**Purpose:** 10 practical copy-paste workflows mapping skills → prompts → actions.

---

## Workflow 1: Audit Dominion Repo

**Goal:** Full repo audit (safety, correctness, architecture)

**Skills/Plugins:**
- `code-review@claude-plugins-official`
- `superpowers@claude-plugins-official` (systematic-debugging)
- `statistical-analysis` (skill)

**Prompt:**
```
Run full Dominion repo audit:

1. Check domdata safety:
   - Run forbidden token scanner
   - Verify no trading code outside allowlisted files
   - Check investor account config

2. Check RAGD health:
   - Query RAGD for recent decisions
   - Verify chunk count matches expected
   - Test REST API endpoints

3. Check feature engineering correctness:
   - Inspect exec_features/*.py for point-in-time safety
   - Verify no future data leakage
   - Use statistical-analysis to check feature distributions

4. Check test coverage:
   - Find untested modules
   - List missing safety tests

5. Generate audit report:
   - Safety issues (high priority)
   - Correctness issues (medium)
   - Code quality issues (low)

Save report to docs/audit_YYYYMMDD.md
```

**Files Read:**
- `domdata/check_no_trading.py`
- `exec_features/*.py`
- `tests/**/*.py`
- `AGENTS.md`, `docs/00_START_HERE/OVERVIEW.md`

**Files Edit:** None (read-only audit)

**Output:** `docs/audit_YYYYMMDD.md`

**Safety Checks:**
- Read-only operation
- No code changes
- Verify forbidden token scanner passes

---

## Workflow 2: Build Point-in-Time-Safe Dataset Feature

**Goal:** Add new feature to dataset pipeline with point-in-time guarantees

**Skills/Plugins:**
- `superpowers@claude-plugins-official` (brainstorming → TDD)
- `polars` (skill)
- `statistical-analysis` (skill)
- `code-review@claude-plugins-official`

**Prompt:**
```
Build point-in-time-safe rolling spread volatility feature:

1. Brainstorm approach:
   - Use /brainstorming to explore design
   - Confirm point-in-time safety requirements
   - Define rolling window (e.g., 60 seconds)

2. Implement in polars:
   - Use polars to compute rolling std(bid-ask spread)
   - Ensure timestamp-based windowing (no future data)
   - Add feature to data_pipeline/features/spread_features.py

3. Validate correctness:
   - Use statistical-analysis to check distribution
   - Verify no NaN/inf values
   - Test edge cases (market open, low liquidity)

4. Write tests:
   - Point-in-time safety test (future data check)
   - Distribution test (expected range)
   - Performance test (speed benchmark)

5. Code review:
   - Run /code-review before commit
   - Fix any safety issues

Files to create/edit:
- data_pipeline/features/spread_features.py (add function)
- tests/test_spread_features.py (new file)
- docs/05_FEATURES/SPREAD_FEATURES.md (update)
```

**Files Read:**
- `data_pipeline/features/*.py`
- `exec_features/spread_features.py`
- `tests/test_*_features.py`

**Files Edit:**
- `data_pipeline/features/spread_features.py` (add function)
- `tests/test_spread_features.py` (new file)
- `docs/05_FEATURES/SPREAD_FEATURES.md` (update)

**Output:**
- New feature function
- Unit tests
- Documentation

**Safety Checks:**
- Point-in-time test passes (no future data)
- No trading code added
- Statistical validation passes

---

## Workflow 3: Research New XAU/USD Macro/Microstructure Signal

**Goal:** Explore new signal idea using academic research + data analysis

**Skills/Plugins:**
- `paper-lookup` (skill)
- `statsmodels` (skill)
- `statistical-analysis` (skill)
- `polars` (skill)

**Prompt:**
```
Research order flow toxicity signal for XAU/USD:

1. Literature review:
   - Use paper-lookup to find papers on "order flow toxicity", "VPIN", "trade imbalance"
   - Summarize top 3 relevant papers
   - Extract feature definitions

2. Explore data:
   - Use polars to load 1 day of XAU/USD tick data
   - Compute tick direction (buy vs sell)
   - Compute volume-synchronized probability of informed trading (VPIN)

3. Statistical validation:
   - Use statsmodels to test for autocorrelation
   - Use statistical-analysis to test if VPIN predicts returns
   - Compute Sharpe ratio of simple threshold strategy

4. Document findings:
   - Create docs/research/order_flow_toxicity_YYYYMMDD.md
   - Include:
     - Paper citations
     - Feature definition (LaTeX formula)
     - Data statistics
     - Preliminary backtest results
     - Next steps (if promising)

No code changes. Research only.
```

**Files Read:**
- `data/normalized/xauusd_ticks_*.parquet`
- Existing research docs

**Files Edit:** None (create new research doc only)

**Output:** `docs/research/order_flow_toxicity_YYYYMMDD.md`

**Safety Checks:**
- No code changes
- No trading execution
- Read-only data access

---

## Workflow 4: Backtest a Signal

**Goal:** Run point-in-time-safe backtest on existing signal

**Skills/Plugins:**
- `scikit-learn` (skill)
- `statsmodels` (skill)
- `statistical-analysis` (skill)
- `polars` (skill)

**Prompt:**
```
Backtest rolling spread volatility signal:

1. Prepare data:
   - Use polars to load dataset_v1
   - Verify no NaN/inf in features
   - Verify no future data (point-in-time check)

2. Train baseline model:
   - Use scikit-learn RandomForest
   - Target: 1-minute forward return (shifted correctly)
   - Features: spread volatility, volume, time features
   - Train/val/test split: 60/20/20

3. Evaluate performance:
   - Compute Sharpe ratio, max drawdown
   - Use statsmodels for return autocorrelation
   - Use statistical-analysis for significance tests

4. Analyze results:
   - Feature importance (scikit-learn)
   - Prediction distribution
   - Time-varying performance

5. Document:
   - Save results to reports/backtest_spread_vol_YYYYMMDD.json
   - Include:
     - Sharpe, drawdown, win rate
     - Feature importance
     - Training time
     - Next steps

No production deployment. Backtest only.
```

**Files Read:**
- `data/train_v1.parquet`
- `data/val_v1.parquet`
- `data/test_v1.parquet`

**Files Edit:**
- `reports/backtest_spread_vol_YYYYMMDD.json` (new file)

**Output:** Backtest report (JSON + markdown summary)

**Safety Checks:**
- Point-in-time data verified
- No live trading
- Correct train/val/test split

---

## Workflow 5: Create ML Experiment

**Goal:** Set up experiment tracking for ML training

**Skills/Plugins:**
- `experiment-tracking-setup@claude-code-plugins-plus`
- `scikit-learn` (skill)
- `pytorch-lightning` (skill, if deep learning)

**Prompt:**
```
Set up MLflow experiment tracking for Dominion:

1. Install MLflow:
   - Add to requirements.txt
   - Install locally

2. Configure experiment tracking:
   - Create mlruns/ directory (add to .gitignore)
   - Create dominion_ai/experiment.py wrapper
   - Log: hyperparams, metrics, artifacts

3. Integrate with scikit-learn:
   - Wrap RandomForest training
   - Log: feature importance, confusion matrix, ROC curve

4. Create experiment CLI:
   - dominion experiment run --model rf --features spread_vol
   - dominion experiment list
   - dominion experiment compare <id1> <id2>

5. Document:
   - docs/04_DEVELOPMENT/EXPERIMENT_TRACKING.md
   - Include: setup, CLI usage, best practices

Files to create:
- dominion_ai/experiment.py
- dominion_ai/cli/experiment.py
- docs/04_DEVELOPMENT/EXPERIMENT_TRACKING.md
```

**Files Read:**
- `dominion_ai/*.py`
- `requirements.txt`

**Files Edit:**
- `requirements.txt` (add mlflow)
- `dominion_ai/experiment.py` (new file)
- `dominion_ai/cli/experiment.py` (new file)
- `docs/04_DEVELOPMENT/EXPERIMENT_TRACKING.md` (new file)
- `.gitignore` (add mlruns/)

**Output:**
- Experiment tracking setup
- CLI commands
- Documentation

**Safety Checks:**
- No trading code
- mlruns/ not committed
- Local-only tracking

---

## Workflow 6: Debug Pipeline Failure

**Goal:** Systematic debugging of data pipeline error

**Skills/Plugins:**
- `superpowers@claude-plugins-official` (systematic-debugging)
- `polars` (skill)
- `statistical-analysis` (skill)

**Prompt:**
```
Debug data pipeline failure in feature computation:

Error: "ValueError: array contains NaN values"

1. Reproduce error:
   - Run exact command that failed
   - Capture full stack trace
   - Identify file + line number

2. Inspect data:
   - Use polars to load input data
   - Check for NaN/inf/missing values
   - Verify data types
   - Check timestamp ordering

3. Root cause analysis:
   - Trace data flow backward
   - Identify where NaN introduced
   - Check edge cases (market hours, holidays)

4. Fix:
   - Add NaN handling (drop, fill, or error)
   - Add validation check upstream
   - Write regression test

5. Verify:
   - Re-run pipeline end-to-end
   - Check output data quality
   - Confirm no new NaNs

Document fix in AGENT_HANDOFF.md
```

**Files Read:**
- `data_pipeline/**/*.py`
- `data/normalized/*.parquet`
- Error logs

**Files Edit:**
- Buggy feature file
- `tests/test_*_features.py` (add regression test)
- `AGENT_HANDOFF.md` (document fix)

**Output:**
- Bug fix
- Regression test
- Handoff doc update

**Safety Checks:**
- No trading code
- Point-in-time safety preserved
- All tests pass

---

## Workflow 7: Add Tests

**Goal:** Increase test coverage for critical modules

**Skills/Plugins:**
- `superpowers@claude-plugins-official` (test-driven-development)
- `statistical-analysis` (skill)

**Prompt:**
```
Add tests for exec_features/spread_features.py:

1. Identify coverage gaps:
   - Run pytest --cov=exec_features/spread_features
   - List untested functions

2. Write unit tests (TDD approach):
   - Test normal cases
   - Test edge cases (empty data, single row, NaN)
   - Test point-in-time safety (no future data)
   - Test statistical properties (distribution, range)

3. Create tests/test_spread_features.py:
   - test_spread_volatility_normal()
   - test_spread_volatility_empty()
   - test_spread_volatility_nan_handling()
   - test_spread_volatility_point_in_time()
   - test_spread_volatility_distribution()

4. Verify:
   - pytest tests/test_spread_features.py
   - Coverage >90%

5. Document:
   - Add docstrings to tests
   - Update docs/04_DEVELOPMENT/TESTING_GUIDE.md

Files to create:
- tests/test_spread_features.py (new file)
```

**Files Read:**
- `exec_features/spread_features.py`
- Existing tests

**Files Edit:**
- `tests/test_spread_features.py` (new file)
- `docs/04_DEVELOPMENT/TESTING_GUIDE.md` (update)

**Output:**
- New test file (>90% coverage)
- Documentation update

**Safety Checks:**
- Tests pass
- Coverage increased
- No functional changes to code

---

## Workflow 8: Generate Dataset Card

**Goal:** Create standardized metadata card for dataset_v1

**Skills/Plugins:**
- `statistical-analysis` (skill)
- `polars` (skill)
- `scientific-writing` (skill, optional)

**Prompt:**
```
Generate dataset card for dataset_v1:

1. Compute statistics:
   - Use polars to load train/val/test splits
   - Compute: row counts, feature distributions, class balance
   - Check for NaN/inf
   - Compute correlation matrix

2. Use statistical-analysis to validate:
   - Test for data leakage (train vs test similarity)
   - Test for distribution shift (train vs val vs test)
   - Test for outliers

3. Create data/DATASET_V1_CARD.md:
   - Dataset name, version, date
   - Purpose (XAU/USD tick feature learning)
   - Data sources (MT5 investor account)
   - Features: name, type, range, distribution
   - Target variable: 1-min forward return
   - Splits: train/val/test sizes, date ranges
   - Known limitations:
     - Investor account (no trade execution)
     - 30-day sample (limited history)
     - Point-in-time features only
   - Intended use: Research only
   - Prohibited use: Live trading without validation

4. Update docs/05_FEATURES/DATASET_V1.md with link

Files to create:
- data/DATASET_V1_CARD.md (new file)
```

**Files Read:**
- `data/train_v1.parquet`
- `data/val_v1.parquet`
- `data/test_v1.parquet`
- `data/DATASET_V1_README.md`

**Files Edit:**
- `data/DATASET_V1_CARD.md` (new file)
- `docs/05_FEATURES/DATASET_V1.md` (update)

**Output:** Dataset card (markdown)

**Safety Checks:**
- Read-only operation
- No code changes
- Document limitations clearly

---

## Workflow 9: Prepare Finance Research Report

**Goal:** Generate macro/sector context report for gold market

**Skills/Plugins:**
- `equity-research@claude-for-financial-services`
- `market-researcher@claude-for-financial-services`
- `paper-lookup` (skill)

**Prompt:**
```
Generate gold market research report (macro context):

1. Equity research:
   - Use /equity-research GOLD (gold ETF)
   - Use /equity-research NEM (Newmont mining)
   - Extract: price targets, catalysts, risks

2. Sector analysis:
   - Use market-researcher to analyze gold mining sector
   - Peer comps: NEM, GOLD, AEM
   - Sector rotation trends

3. Academic context:
   - Use paper-lookup to find papers on "gold price drivers"
   - Summarize: interest rates, USD strength, geopolitical risk

4. Synthesize:
   - Create docs/research/gold_market_context_YYYYMMDD.md
   - Include:
     - Executive summary
     - Equity analysis (GLD, NEM)
     - Sector positioning
     - Macro drivers (Fed policy, USD, inflation)
     - XAU/USD implications
     - References

This is macro context ONLY. Not for XAU/USD signals.
```

**Files Read:**
- Existing research docs

**Files Edit:**
- `docs/research/gold_market_context_YYYYMMDD.md` (new file)

**Output:** Research report (markdown)

**Safety Checks:**
- No trading code
- Macro context only (not signals)
- Educational use disclaimer

---

## Workflow 10: Create Deployment/CI Plan

**Goal:** Plan GitHub Actions CI for Dominion safety tests

**Skills/Plugins:**
- `ci-cd-pipeline-builder@claude-code-plugins-plus`
- `superpowers@claude-plugins-official` (writing-plans)

**Prompt:**
```
Design GitHub Actions CI for Dominion:

1. Define CI stages:
   - Safety: forbidden token scanner, domdata order-send blocked
   - Correctness: pytest, RAGD tests
   - Performance: feature computation benchmarks
   - Docs: check links, generate coverage report

2. Create .github/workflows/dominion_ci.yml:
   - Trigger: push, PR to main
   - Jobs:
     - safety-check (domdata/check_no_trading.py)
     - unit-tests (pytest)
     - ragd-tests (ragd/build + ctest)
     - feature-tests (data_pipeline tests)
   - Fail fast on safety violations

3. Add CI badge to README.md

4. Document:
   - docs/04_DEVELOPMENT/CI_CD_GUIDE.md
   - Include: pipeline stages, how to debug failures

5. Plan (do not implement yet):
   - Use /writing-plans to create implementation plan
   - Review with user before implementation

Files to create (plan only):
- .github/workflows/dominion_ci.yml (planned)
- docs/04_DEVELOPMENT/CI_CD_GUIDE.md (planned)

Output: Implementation plan (not code)
```

**Files Read:**
- Existing test files
- `domdata/check_no_trading.py`
- `.gitignore`

**Files Edit:** None (planning phase)

**Output:** CI implementation plan (markdown)

**Safety Checks:**
- No auto-deploy
- Manual approval before CI implementation
- Safety checks run first

---

## 5 Copy-Paste Prompts (Ready to Use)

### 1. Daily Audit
```
Run daily Dominion safety audit: check domdata forbidden tokens, verify no trading code, check RAGD health. Report safety issues only.
```

### 2. Point-in-Time Feature
```
Use polars to add rolling bid-ask spread volatility feature to data_pipeline/features/spread_features.py. Ensure point-in-time safety (no future data). Add tests. Use statistical-analysis to validate distribution.
```

### 3. Backtest Signal
```
Use scikit-learn to train RandomForest on dataset_v1 predicting 1-min forward returns. Use statsmodels to validate. Compute Sharpe, max drawdown. Save report to reports/backtest_YYYYMMDD.json.
```

### 4. Debug Pipeline
```
Debug "ValueError: array contains NaN" in data_pipeline. Use polars to inspect input data. Trace root cause. Add NaN handling + regression test. Document fix in AGENT_HANDOFF.md.
```

### 5. Research Paper Lookup
```
Use paper-lookup to find 5 papers on "tick data microstructure" or "order flow toxicity". Summarize key findings. Document in docs/research/literature_YYYYMMDD.md. No code changes.
```

---

## Quick Reference

### Check Available Skills/Plugins
```bash
claude plugin list
npx skills list
```

### Invoke Plugin
```bash
/equity-research GOLD
/code-review
/commit
/brainstorming
```

### Invoke Skill (via prompt)
```
Use statsmodels to test Granger causality
Use polars to aggregate ticks
Use scikit-learn to train baseline
```

### RAGD-First Workflow
```bash
# Before work
dominion ragd-query "feature engineering point in time safety"

# After decisions
dominion ragd-remember "Added rolling spread volatility feature with 60s window"
```
