---
synced: 2026-05-19 18:24
---
# Superhuman Feature Ledger

## Agent 2 Scope

| Feature | Status | Evidence | Notes |
|---|---:|---|---|
| S06 Retrieval confidence and escalation | Complete | `dominion ask "how does the handoff protocol work" --json` score `0.91`; `test_confidence.py` | Low confidence escalates once, then refuses below threshold |
| S07 Context budget optimizer | Complete | `test_budget.py`; context citations preserved | Greedy value/cost optimizer; compresses low-value chunks |
| S08 Query-to-code trace explorer | Complete | `dominion trace ad51518679964fab8b78802762e7d5bd` | Shows plan/retrieve/rrf/filter/rerank/confidence/assemble |
| S09 Local model performance governor | Retired by Agent 6 | `scripts/bin/llm`; `dominion ask --generate --json` | Frontier agents handle generation; RAGD retrieval remains local-first |

## Explicitly Deferred

- External embedding runs are interface-ready and fail closed until `RAGD_EMBED_API_KEY` is configured.
- Full Agent 1 benchmark harness registration is not implemented; `dominion bench` supplies lightweight local measurements.
- The governor consumes Agent 1 `dominion_loader.api.hw_probe`; a `TEMP_ADAPTER(agent-1)` fallback remains for older checkouts where the interface is absent.
