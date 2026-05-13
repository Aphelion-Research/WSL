# Superhuman Feature Ledger

## Agent 2 Scope

| Feature | Status | Evidence | Notes |
|---|---:|---|---|
| S06 Retrieval confidence and escalation | Complete | `dominion ask "how does the handoff protocol work" --json` score `0.91`; `test_confidence.py` | Low confidence escalates once, then refuses below threshold |
| S07 Context budget optimizer | Complete | `test_budget.py`; context citations preserved | Greedy value/cost optimizer; compresses low-value chunks |
| S08 Query-to-code trace explorer | Complete | `dominion trace ad51518679964fab8b78802762e7d5bd` | Shows plan/retrieve/rrf/filter/rerank/confidence/assemble |
| S09 Local model performance governor | Complete | `llm doctor --json`; `test_governor.py` | 4 GB class profile refuses configured 3.8 GB model, falls back retrieve-only |

## Explicitly Deferred

- Embedding and LLM rerank are interface-ready but not enabled by default.
- Full Agent 1 benchmark harness registration is not implemented; `dominion bench` supplies lightweight local measurements.
- The governor consumes Agent 1 `dominion_loader.api.hw_probe`; a `TEMP_ADAPTER(agent-1)` fallback remains for older checkouts where the interface is absent.
