---
synced: 2026-05-21 22:42
---
# Agent 2 Handoff

Timestamp: 2026-05-13T21:49:49Z

## What Landed

- New `dominion_ai/` package with planner, RAGD client, hybrid retrieval composition, heuristic rerank, confidence scoring, budgeted context assembly, trace rendering, eval runner, ledger query, and CLI handlers.
- Additive CLI: `dominion ask/search/explain/trace/eval/ledger/graph/bench`.
- Local generation support landed in Agent 2 and was retired by Agent 6; frontier agents now handle generation.
- `dominion-ui --once` now includes "Latest queries" and "Latest decisions".
- Focused Agent 2 tests passed at the time; Phase 6 validation now covers `dominion_ai/tests` plus RAG retrieval packages.
- Full configured tests: `python -m pytest -q` => `42 passed`.

## Important Boundaries

- RAGD remains the only retrieval spine. Agent 2 calls RAGD `/query`; it does not create a parallel index.
- `TEMP_ADAPTER(agent-1)` derives `content_hash` until RAGD query results expose it.
- `dominion hw probe --json` now consumes `dominion_loader.api.hw_probe`; `TEMP_ADAPTER(agent-1)` remains only as a fallback for older checkouts.
- `dominion ask --generate` now stays retrieve-only and reports that Claude Code, Codex, or Cursor handles generation.

## Evidence

```bash
dominion search "agent handoff" --top-k 3 --json
dominion ask "how does the handoff protocol work" --json
dominion ask "how does the handoff protocol work" --generate --json
dominion explain --chunk 1024 --json
dominion trace ad51518679964fab8b78802762e7d5bd
dominion eval --bundle dominion_ai/tests/eval_fixtures/tiny --top-k 10 --json
dominion ledger list --kind decision --since 7d --json
dominion embed stats --json
dominion vault status --json
dominion-ui --once
```

## Next Best Tasks

1. Agent 1 should add `content_hash` and `document_id` to RAGD `/query` results, then remove `TEMP_ADAPTER(agent-1)` from `dominion_ai/ragd_client.py`.
2. Keep `dominion_loader.api.hw_probe` stable for diagnostics, but it no longer gates generation.
3. Configure `RAGD_EMBED_API_KEY` and run `dominion embed run` when semantic retrieval is required.
4. Register `dominion_ai.bench` with Agent 1's benchmark harness once that extension point is available.
