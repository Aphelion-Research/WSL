---
doc_type: reference
system: Dominion
audience: [owner, ai_agent]
status: current
last_updated: 2026-05-20
tags: [claude-code, skills, plugins, workflow]
---

# Claude Code Skill Routing Map

**Purpose:** Map installed Claude Code plugins/skills → concrete Dominion/HYDRA workflows.

**Last Updated:** 2026-05-20  
**Total Plugins:** 39 installed  
**Total Skills:** 138 installed  
**Marketplaces:** 5 (official, caveman, plugins-plus, equity-research, financial-services)

---

## Finance / Market Research

### equity-research@claude-for-financial-services
- **Source:** Plugin (financial-services marketplace)
- **Use:** Generate Wall Street-grade equity research reports for macro context (e.g., gold ETFs GLD/IAU/GLDM, mining stocks)
- **When NOT to use:** XAU/USD intraday signals, microstructure analysis, point-in-time features
- **Example:** `/equity-research GOLD --detailed`
- **Priority:** Occasional (macro research only)

### trading-ideas@claude-equity-research-marketplace
- **Source:** Plugin (equity-research marketplace)
- **Use:** Options flow + insider activity for equity tickers (gold miners: NEM, GOLD, AEM)
- **When NOT to use:** Forex/commodity analysis, intraday signals, backtesting
- **Example:** `/trading-ideas:research NEM`
- **Priority:** Occasional (equity context only)

### financial-analysis@claude-for-financial-services
- **Source:** Plugin (financial-services marketplace)
- **Use:** DCF, comps, valuation templates for fundamental equity analysis
- **When NOT to use:** Quant signal research, feature engineering, backtesting
- **Example:** Invoke via prompt: "Run DCF valuation for Newmont (NEM)"
- **Priority:** Avoid (not relevant to XAU/USD quant)

### market-researcher@claude-for-financial-services
- **Source:** Plugin (financial-services marketplace)
- **Use:** Sector overviews, competitive landscape, peer comps (gold sector ETFs/miners)
- **When NOT to use:** Intraday trading signals, microstructure, ML features
- **Example:** Invoke via prompt: "Generate market research report on gold mining sector"
- **Priority:** Occasional (sector context)

### investment-banking@claude-for-financial-services
- **Source:** Plugin (financial-services marketplace)
- **Use:** Pitch decks, LBO models (not applicable to Dominion)
- **When NOT to use:** Always
- **Priority:** Avoid

### pitch-agent@claude-for-financial-services
- **Source:** Plugin (financial-services marketplace)
- **Use:** Generate branded pitch decks (not applicable)
- **When NOT to use:** Always
- **Priority:** Avoid

---

## Quant Research / Statistics

### statsmodels
- **Source:** Skill (scientific-agent-skills)
- **Use:** Time series analysis (ARIMA, VAR, VECM), regression, econometric validation
- **When NOT to use:** ML model training, neural networks, real-time inference
- **Example:** "Use statsmodels to run Granger causality test on XAU/USD tick volume vs spread"
- **Priority:** Daily (validation + feature research)

### pymc
- **Source:** Skill (scientific-agent-skills)
- **Use:** Bayesian inference, probabilistic models, uncertainty quantification for signal priors
- **When NOT to use:** Fast backtesting, production inference, deterministic features
- **Example:** "Use pymc to model XAU/USD bid-ask spread distribution with hierarchical priors"
- **Priority:** Occasional (research phase)

### sympy
- **Source:** Skill (scientific-agent-skills)
- **Use:** Symbolic math for feature derivation, calculus, closed-form solutions
- **When NOT to use:** Numerical computation, data processing, ML
- **Example:** "Use sympy to derive analytical gradient of custom loss function"
- **Priority:** Occasional (math validation)

### statistical-analysis
- **Source:** Skill (scientific-agent-skills)
- **Use:** Hypothesis testing, p-values, distribution checks, feature correlation
- **When NOT to use:** Implementation, ML training, backtesting
- **Example:** "Use statistical-analysis to test if XAU/USD tick arrival is Poisson-distributed"
- **Priority:** Daily (feature validation)

### pymoo
- **Source:** Skill (scientific-agent-skills)
- **Use:** Multi-objective optimization (Sharpe vs drawdown, return vs turnover)
- **When NOT to use:** Single-objective optimization, gradient descent, ML training
- **Example:** "Use pymoo to optimize portfolio weights for max Sharpe, min drawdown"
- **Priority:** Occasional (optimization research)

### timesfm-forecasting
- **Source:** Skill (scientific-agent-skills)
- **Use:** Time series forecasting research (NOT for production signals)
- **When NOT to use:** Point-in-time features, backtesting, real-time inference
- **Example:** "Use timesfm-forecasting to explore tick arrival rate forecasting"
- **Priority:** Avoid (use statsmodels instead)

---

## Scientific Math

### polars
- **Source:** Skill (scientific-agent-skills)
- **Use:** Fast DataFrame ops (replaces pandas for large data processing)
- **When NOT to use:** Small datasets (<10k rows), existing pandas code that works
- **Example:** "Use polars to aggregate 10M XAU/USD ticks into 1-second OHLCV bars"
- **Priority:** Daily (data pipeline optimization)

### dask
- **Source:** Skill (scientific-agent-skills)
- **Use:** Parallel/distributed DataFrame ops (for multi-day tick processing)
- **When NOT to use:** Single-threaded code, small datasets, real-time inference
- **Example:** "Use dask to process 30 days of XAU/USD ticks in parallel"
- **Priority:** Occasional (batch processing)

### vaex
- **Source:** Skill (scientific-agent-skills)
- **Use:** Out-of-core DataFrames (memory-mapped, lazy evaluation)
- **When NOT to use:** In-memory datasets, real-time processing
- **Example:** "Use vaex to explore 100GB tick dataset without loading into RAM"
- **Priority:** Avoid (use polars + DuckDB instead)

### networkx
- **Source:** Skill (scientific-agent-skills)
- **Use:** Graph algorithms (dependency graphs, feature DAGs)
- **When NOT to use:** Time series analysis, ML, backtesting
- **Example:** "Use networkx to visualize feature dependency graph"
- **Priority:** Occasional (architecture docs)

---

## Data Engineering

### database-migration-manager@claude-code-plugins-plus
- **Source:** Plugin (plugins-plus marketplace)
- **Use:** Schema migrations for DuckDB/SQLite (future work)
- **When NOT to use:** RAGD schema (use RAGD tests), MT5 data (read-only)
- **Example:** Invoke via prompt: "Generate Alembic migration for new feature table"
- **Priority:** Avoid (no active migrations)

### polars (data engineering context)
- **Source:** Skill (scientific-agent-skills)
- **Use:** Point-in-time-safe feature engineering, tick → bar aggregation, join operations
- **When NOT to use:** Real-time inference (use C++ exec_features)
- **Example:** "Use polars to create point-in-time-safe rolling spread features"
- **Priority:** Daily (feature research)

### zarr-python
- **Source:** Skill (scientific-agent-skills)
- **Use:** Chunked, compressed, cloud-friendly array storage (future work)
- **When NOT to use:** Current Parquet pipeline, small datasets
- **Example:** "Use zarr-python to store 1TB tick data with metadata"
- **Priority:** Avoid (stick with Parquet)

---

## ML / Experiment Tracking

### scikit-learn
- **Source:** Skill (scientific-agent-skills)
- **Use:** Classical ML (RandomForest, XGBoost baseline), feature selection, cross-validation
- **When NOT to use:** Deep learning, online learning, real-time inference
- **Example:** "Use scikit-learn to train RandomForest baseline on dataset_v1"
- **Priority:** Daily (baseline models)

### pytorch-lightning
- **Source:** Skill (scientific-agent-skills)
- **Use:** Structured PyTorch training (if/when moving to deep learning)
- **When NOT to use:** Classical ML, research experiments, production inference
- **Example:** "Use pytorch-lightning to train LSTM on tick sequences"
- **Priority:** Avoid (no deep learning yet)

### experiment-tracking-setup@claude-code-plugins-plus
- **Source:** Plugin (plugins-plus marketplace)
- **Use:** MLflow/W&B setup for experiment tracking
- **When NOT to use:** Current local experiment tracking (JSON reports)
- **Example:** Invoke via prompt: "Set up MLflow tracking for Dominion experiments"
- **Priority:** Occasional (after 10+ experiments)

### shap
- **Source:** Skill (scientific-agent-skills)
- **Use:** Model explainability (SHAP values for feature importance)
- **When NOT to use:** Linear models (use coefficients), research phase (use EDA first)
- **Example:** "Use shap to explain RandomForest predictions on dataset_v1"
- **Priority:** Occasional (after baseline models)

### stable-baselines3
- **Source:** Skill (scientific-agent-skills)
- **Use:** Reinforcement learning (if exploring RL for execution)
- **When NOT to use:** Supervised learning, backtesting, current workflow
- **Example:** "Use stable-baselines3 to train PPO agent for order execution"
- **Priority:** Avoid (no RL yet)

---

## DevOps / Infra

### github@claude-plugins-official
- **Source:** Plugin (official marketplace)
- **Use:** PR management, issue tracking, code review automation
- **When NOT to use:** Local git operations (use Bash), commit messages (use caveman)
- **Example:** Invoke via prompt: "Create PR for feature branch agent1-content"
- **Priority:** Occasional (PR automation)

### ci-cd-pipeline-builder@claude-code-plugins-plus
- **Source:** Plugin (plugins-plus marketplace)
- **Use:** GitHub Actions CI for tests, safety scanner, dataset validation
- **When NOT to use:** Local testing, tmux workflows, manual validation
- **Example:** Invoke via prompt: "Build GitHub Actions workflow for domdata safety tests"
- **Priority:** Occasional (after 5+ manual test runs)

### terraform-module-builder@claude-code-plugins-plus
- **Source:** Plugin (plugins-plus marketplace)
- **Use:** IaC for future AWS deployment (not current priority)
- **When NOT to use:** Local WSL/Debian setup, tmux, SSH
- **Example:** Invoke via prompt: "Generate Terraform module for EC2 + EFS deployment"
- **Priority:** Avoid (local-first platform)

### jeremy-vertex-ai@claude-code-plugins-plus
- **Source:** Plugin (plugins-plus marketplace)
- **Use:** Google Cloud Vertex AI integration (not applicable)
- **When NOT to use:** Always
- **Priority:** Avoid

---

## Documentation / RAG

### context7@claude-plugins-official
- **Source:** Plugin (official marketplace)
- **Use:** Live library docs (polars, statsmodels, scikit-learn)
- **When NOT to use:** Dominion-specific code (use RAGD), standard library docs
- **Example:** Automatically invoked when asking "How do I use polars lazy API?"
- **Priority:** Daily (library questions)

### paper-lookup
- **Source:** Skill (scientific-agent-skills)
- **Use:** ArXiv/research paper search for quant finance papers
- **When NOT to use:** Dominion docs (use RAGD), general questions
- **Example:** "Use paper-lookup to find papers on tick data microstructure"
- **Priority:** Occasional (research phase)

### literature-review
- **Source:** Skill (scientific-agent-skills)
- **Use:** Systematic review generation from papers (for research reports)
- **When NOT to use:** Code implementation, feature engineering
- **Example:** "Use literature-review to summarize 10 papers on order flow toxicity"
- **Priority:** Avoid (manual literature review faster)

### pyzotero
- **Source:** Skill (scientific-agent-skills)
- **Use:** Zotero citation management (if using Zotero)
- **When NOT to use:** Simple citations, inline references
- **Example:** "Use pyzotero to export citations from 'Microstructure' collection"
- **Priority:** Avoid (not using Zotero)

### scientific-writing
- **Source:** Skill (scientific-agent-skills)
- **Use:** Research report drafting (for external publication)
- **When NOT to use:** Internal docs, code comments, agent reports
- **Example:** "Use scientific-writing to draft methods section for signal paper"
- **Priority:** Avoid (focus on code, not papers)

---

## Codebase Maintenance

### code-review@claude-plugins-official
- **Source:** Plugin (official marketplace)
- **Use:** Automated code review before PR (safety, style, correctness)
- **When NOT to use:** Live coding, exploratory work, small edits
- **Example:** Invoke via skill: `/code-review`
- **Priority:** Daily (before commits)

### code-simplifier@claude-plugins-official
- **Source:** Plugin (official marketplace)
- **Use:** Refactor complex code, reduce duplication, improve readability
- **When NOT to use:** Working code, performance-critical paths, first draft
- **Example:** Invoke via skill: `/simplify`
- **Priority:** Occasional (after 3+ similar functions)

### feature-dev@claude-plugins-official
- **Source:** Plugin (official marketplace)
- **Use:** Plan + implement new features (e.g., new exec_features module)
- **When NOT to use:** Bug fixes, docs, small edits
- **Example:** Invoke via skill: `/feature-dev`
- **Priority:** Daily (new features)

### hookify@claude-plugins-official
- **Source:** Plugin (official marketplace)
- **Use:** Create pre-commit hooks (safety scanner, forbidden tokens, tests)
- **When NOT to use:** Manual validation, exploratory work
- **Example:** Invoke via skill: `/hookify`
- **Priority:** Occasional (after repeated manual checks)

### caveman@caveman
- **Source:** Plugin (caveman marketplace)
- **Use:** Terse output mode (active now)
- **When NOT to use:** Teaching, explanations, user onboarding
- **Example:** `/caveman full` (already active)
- **Priority:** Daily (personal preference)

### commit-commands@claude-plugins-official
- **Source:** Plugin (official marketplace)
- **Use:** Smart git commit messages, auto-stage, commit-push-pr
- **When NOT to use:** Complex merge conflicts, manual staging
- **Example:** Invoke via skill: `/commit`
- **Priority:** Daily (commit automation)

### superpowers@claude-plugins-official
- **Source:** Plugin (official marketplace)
- **Use:** Brainstorming, TDD, systematic debugging, git worktrees
- **When NOT to use:** Simple tasks, exploratory coding
- **Example:** Invoke via skill: `/brainstorming` before new features
- **Priority:** Daily (workflow discipline)

---

## Summary: Top 10 Most Useful

1. **statsmodels** (skill) — time series + econometric validation
2. **polars** (skill) — fast DataFrame ops for feature engineering
3. **scikit-learn** (skill) — baseline ML models
4. **statistical-analysis** (skill) — hypothesis testing + correlation
5. **context7** (plugin) — live library docs
6. **code-review** (plugin) — pre-commit code review
7. **commit-commands** (plugin) — smart commit automation
8. **superpowers** (plugin) — brainstorming + TDD workflows
9. **github** (plugin) — PR automation
10. **equity-research** (plugin) — macro/sector context (occasional)

---

## Priority Levels

- **Daily:** statsmodels, polars, scikit-learn, statistical-analysis, context7, code-review, commit-commands, superpowers
- **Occasional:** pymc, equity-research, market-researcher, shap, paper-lookup, github, ci-cd-pipeline-builder
- **Avoid:** financial-analysis, investment-banking, pitch-agent, timesfm-forecasting, vaex, database-migration-manager, zarr-python, pytorch-lightning, stable-baselines3, terraform-module-builder, jeremy-vertex-ai, literature-review, pyzotero, scientific-writing

---

## Safety Rules

1. **Finance plugins** → public market research ONLY (not XAU/USD signals)
2. **Scientific/math skills** → validation, statistics, optimization, feature research
3. **Data/ML skills** → inspect local code first, never override point-in-time safety
4. **RAGD-first** → query RAGD before editing, remember after decisions
5. **No future data** → never use future data in features (point-in-time safety)
6. **No auto-install** → never install new plugins unless explicitly requested

---

## Quick Reference

### Invoke Plugin Command
```bash
/equity-research GOLD
/trading-ideas:research NEM
/code-review
/commit
/brainstorming
```

### Invoke Skill via Prompt
```
Use statsmodels to run Granger causality test on tick volume vs spread
Use polars to aggregate ticks into 1-second bars
Use scikit-learn to train RandomForest baseline
Use statistical-analysis to test Poisson distribution assumption
Use context7 to lookup polars lazy API docs
```

### Check Available
```bash
claude plugin list
npx skills list
```
