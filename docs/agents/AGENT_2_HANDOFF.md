# Agent 2 Handoff

Timestamp: 2026-05-13T21:49:49Z

## What Landed

- New `dominion_ai/` package with planner, RAGD client, hybrid retrieval composition, heuristic rerank, confidence scoring, budgeted context assembly, trace rendering, eval runner, ledger query, and CLI handlers.
- Additive CLI: `dominion ask/search/explain/trace/eval/ledger/graph/bench`.
- Local LLM provider registry, Ollama + mock providers, and 4 GB VRAM governor.
- `dominion-ui --once` now includes "Latest queries" and "Latest decisions".
- Focused tests: `python -m pytest -q dominion_ai/tests local_llm/tests` => `26 passed`.
- Full configured tests: `python -m pytest -q` => `42 passed`.

## Important Boundaries

- RAGD remains the only retrieval spine. Agent 2 calls RAGD `/query`; it does not create a parallel index.
- `TEMP_ADAPTER(agent-1)` derives `content_hash` until RAGD query results expose it.
- `dominion hw probe --json` now consumes `dominion_loader.api.hw_probe`; `TEMP_ADAPTER(agent-1)` remains only as a fallback for older checkouts.
- Current Ollama model is present, but the governor refuses it on the 4 GB class GPU because the installed model is about 3.8 GB and exceeds the 3.5 GB safety ceiling.

## Evidence

```bash
dominion search "agent handoff" --top-k 3 --json
dominion ask "how does the handoff protocol work" --json
dominion ask "how does the handoff protocol work" --generate --json
dominion explain --chunk 1024 --json
dominion trace ad51518679964fab8b78802762e7d5bd
dominion eval --bundle dominion_ai/tests/eval_fixtures/tiny --top-k 10 --json
dominion ledger list --kind decision --since 7d --json
llm doctor --json
dominion-ui --once
```

## Next Best Tasks

1. Agent 1 should add `content_hash` and `document_id` to RAGD `/query` results, then remove `TEMP_ADAPTER(agent-1)` from `dominion_ai/ragd_client.py`.
2. Keep `dominion_loader.api.hw_probe` stable; Agent 2 now consumes it for governor decisions.
3. Add a smaller configured local model under the 3.5 GB ceiling if generation on the 4 GB GPU is required.
4. Register `dominion_ai.bench` with Agent 1's benchmark harness once that extension point is available.
