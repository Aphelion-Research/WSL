# Claude Code Configuration for Dominion

**Platform:** Dominion V2 (XAU/USD quant research workstation)  
**Status:** Local-first, agent-native, read-only data bridge  
**Last Updated:** 2026-05-20

---

## Core Contracts

See `AGENTS.md` for full platform contract. Key rules:

1. **Read-only data bridge:** Never add trading execution (no order_send, no order_check outside safety tests)
2. **Point-in-time safety:** Features must never use future data
3. **RAGD-first workflow:** Query before editing, remember after decisions
4. **Validate before claiming success:** Run safety scanner, tests, doctor checks
5. **Preserve working systems:** MT5/Wine, RAGD, tmux sessions, Tailscale/SSH

---

## Local Skills / Plugin Usage

### Installed Marketplaces
- **claude-plugins-official** (Anthropic official)
- **caveman** (terse output mode)
- **claude-code-plugins-plus** (community plugins)
- **claude-equity-research-marketplace** (equity research)
- **claude-for-financial-services** (financial services)

### Installed Plugins: 39
See: `claude plugin list`

### Installed Skills: 138
See: `npx skills list`

### Routing Map
See: `docs/claude_skill_routing.md` for full skill → workflow mapping.

---

## Skill Usage Rules

### Finance Plugins
**Use:** Public market research, macro/sector context ONLY  
**Never:** XAU/USD intraday signals, microstructure analysis, live trading  
**Examples:**
- `/equity-research GOLD` → gold ETF research
- `/market-researcher` → gold mining sector analysis

**Plugins:**
- `equity-research@claude-for-financial-services`
- `trading-ideas@claude-equity-research-marketplace`
- `market-researcher@claude-for-financial-services`

### Scientific/Math Skills
**Use:** Validation, statistics, optimization, feature research  
**Primary:**
- `statsmodels` → time series, econometric tests (Granger causality, VAR)
- `pymc` → Bayesian inference, uncertainty quantification
- `statistical-analysis` → hypothesis testing, distributions, p-values
- `pymoo` → multi-objective optimization (Sharpe vs drawdown)
- `sympy` → symbolic math, feature derivation

**Example:**
```
Use statsmodels to test if tick volume Granger-causes spread changes
```

### Data/ML Skills
**Use:** Implementation help AFTER inspecting local code  
**Never:** Override point-in-time safety, use future data  
**Primary:**
- `polars` → fast DataFrame ops (preferred over pandas)
- `scikit-learn` → baseline ML models (RandomForest, XGBoost)
- `shap` → model explainability (after baseline models)

**Example:**
```
Use polars to aggregate 10M ticks into 1-second OHLCV bars with point-in-time safety
```

### Documentation/RAG Skills
**Use:** Library docs, paper lookup  
**Primary:**
- `context7` → live library docs (polars, statsmodels, scikit-learn)
- `paper-lookup` → ArXiv/research paper search

**Example:**
```
Use paper-lookup to find papers on order flow toxicity
```

### Codebase Maintenance Plugins
**Use:** Code review, commits, refactoring, debugging  
**Primary:**
- `code-review` → pre-commit review
- `commit-commands` → smart commit messages
- `superpowers` → brainstorming, TDD, systematic debugging
- `code-simplifier` → refactor complex code

**Example:**
```
/code-review  # before committing
/commit       # smart commit message
/brainstorming  # before new features
```

---

## Critical Constraints

### Point-in-Time Safety
**Rule:** Features must NEVER use future data.

**Check:**
```python
# BAD: uses future data
df['rolling_mean'] = df['price'].rolling(60).mean()  # looks forward

# GOOD: point-in-time safe
df['rolling_mean'] = df['price'].shift(1).rolling(60).mean()  # lag by 1
```

**Validation:**
```python
# Test: verify no future data
def test_point_in_time_safety(feature_fn):
    data = load_ticks()
    features = feature_fn(data)
    
    # Feature at time t must only use data from t-N to t (not t+1)
    assert features.index == data.index
    assert not any(features.notna() & data.shift(-1).isna())  # no lookahead
```

### Forbidden Trading Tokens
**Rule:** Never use trading tokens outside allowlisted safety test files.

**Forbidden:**
- `order_send`
- `order_check` (except in safety tests)
- `TRADE_ACTION_DEAL`
- `TRADE_ACTION_PENDING`
- `POSITION_CLOSE`

**Scanner:**
```bash
python ~/Dominion/domdata/check_no_trading.py
```

**Allowlisted files:**
- `domdata/check_no_trading.py` (safety scanner itself)
- `domdata/tests/test_trading_blocked.py` (safety tests)

### Data Sources
**Rule:** Only use read-only MT5 data via domdata CLI.

**Safe:**
```bash
domdata xautick          # latest tick
domdata xaurates         # latest rates
domdata xauticks --start 2026-05-11T00:00:00Z --count 100
```

**Blocked:**
```bash
domdata order-send  # blocked at CLI level
```

### No Auto-Install
**Rule:** Never install new plugins/skills unless explicitly requested.

**Check installed:**
```bash
claude plugin list
npx skills list
```

---

## Workflow Patterns

### Daily Workflow
1. **Morning audit:** Check domdata safety, RAGD health
2. **RAGD query:** Query before editing (`dominion ragd-query "topic"`)
3. **Code review:** `/code-review` before commits
4. **Smart commit:** `/commit` for commit messages
5. **RAGD remember:** Remember decisions (`dominion ragd-remember "decision"`)

### Feature Engineering Workflow
1. **Brainstorm:** `/brainstorming` → design feature
2. **Implement:** Use `polars` for fast DataFrame ops
3. **Validate:** Use `statistical-analysis` for distribution checks
4. **Test:** Point-in-time safety test + unit tests
5. **Review:** `/code-review` before commit

### Debugging Workflow
1. **Reproduce:** Exact command + full stack trace
2. **Inspect:** Use `polars` to inspect data
3. **Root cause:** Trace data flow backward
4. **Fix:** Add NaN handling + validation
5. **Test:** Regression test
6. **Document:** Update `AGENT_HANDOFF.md`

### Research Workflow
1. **Literature:** Use `paper-lookup` for papers
2. **Data exploration:** Use `polars` + `statistical-analysis`
3. **Modeling:** Use `statsmodels` for econometric tests
4. **Validation:** Use `scikit-learn` for baseline models
5. **Report:** Document in `docs/research/`

---

## Common Prompts

### Audit
```
Run daily Dominion safety audit: check domdata forbidden tokens, verify no trading code, check RAGD health.
```

### Feature Engineering
```
Use polars to add rolling bid-ask spread volatility feature with 60s window. Ensure point-in-time safety. Add tests. Use statistical-analysis to validate distribution.
```

### Backtesting
```
Use scikit-learn to train RandomForest on dataset_v1 predicting 1-min forward returns. Compute Sharpe, max drawdown. Save report to reports/backtest_YYYYMMDD.json.
```

### Debugging
```
Debug "ValueError: array contains NaN" in data_pipeline. Use polars to inspect input data. Trace root cause. Add NaN handling + regression test.
```

### Research
```
Use paper-lookup to find papers on "tick data microstructure". Summarize key findings. Document in docs/research/literature_YYYYMMDD.md.
```

---

## Quick Reference

### Check Skills/Plugins
```bash
claude plugin list
npx skills list
cat docs/claude_skill_routing.md  # full routing map
cat docs/claude_workflows.md      # 10 practical workflows
```

### Invoke Plugin
```bash
/equity-research GOLD
/code-review
/commit
/brainstorming
```

### Invoke Skill
```
Use statsmodels to test Granger causality
Use polars to aggregate ticks
Use scikit-learn to train baseline
```

### RAGD Commands
```bash
dominion ragd-query "topic"
dominion ragd-remember "decision"
```

### Safety Commands
```bash
python domdata/check_no_trading.py  # forbidden token scanner
domdata doctor                       # health check
domdata order-send || true           # verify blocked
```

---

## Top 10 Most Useful Skills/Plugins

1. **statsmodels** (skill) → time series + econometric validation
2. **polars** (skill) → fast DataFrame ops for feature engineering
3. **scikit-learn** (skill) → baseline ML models
4. **statistical-analysis** (skill) → hypothesis testing + correlation
5. **context7** (plugin) → live library docs
6. **code-review** (plugin) → pre-commit code review
7. **commit-commands** (plugin) → smart commit automation
8. **superpowers** (plugin) → brainstorming + TDD workflows
9. **github** (plugin) → PR automation
10. **equity-research** (plugin) → macro/sector context (occasional)

---

## Documentation

- **Skill routing:** `docs/claude_skill_routing.md`
- **Workflows:** `docs/claude_workflows.md`
- **Platform contract:** `AGENTS.md`
- **System overview:** `docs/00_START_HERE/OVERVIEW.md`
- **RAGD docs:** `docs/02_RAGD/`
- **Development guide:** `docs/04_DEVELOPMENT/`

---

## Contact

- **Owners:** Matin, Dan
- **Collaboration:** tmux + SSH + Tailscale
- **Sessions:** `tmux ls` (ragd, dominion, ssh sessions)
