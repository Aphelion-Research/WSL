# Dominion Agent 2 Performance Baseline

## Retrieval Before

Command:

```bash
curl -s -X POST http://127.0.0.1:7474/query -H 'Content-Type: application/json' -d '{"q":"agent handoff","top_k":10,"mode":"hybrid"}' | jq '{elapsed_ms, count:(.results|length), top1:(.results[0] // {})}'
```

Result captured 2026-05-13T21:40Z:

- RAGD direct `elapsed_ms`: 26
- Result count: 10
- Top-1: `/home/Martin/Dominion/AGENT_HANDOFF.md:1-2` chunk `1024`

## Agent 2 After

Command:

```bash
dominion bench --suite retrieval --iterations 3
dominion bench --suite e2e --iterations 3
dominion bench --suite generation --iterations 1
```

Results captured 2026-05-13T21:49Z:

| Metric | Before | After | Delta | Method |
|---|---:|---:|---:|---|
| RAGD direct hybrid query elapsed | 26 ms | n/a | n/a | Direct `/query` baseline |
| `dominion ask` retrieve-only p50 | n/a | 52.01 ms | n/a | `dominion bench --suite retrieval --iterations 3` |
| `dominion ask` retrieve-only p95 | n/a | 55.25 ms | n/a | `dominion bench --suite retrieval --iterations 3` |
| `dominion ask` e2e p50 | n/a | 50.86 ms | n/a | `dominion bench --suite e2e --iterations 3` |
| `dominion ask --generate` p50 | n/a | retrieve-only | n/a | Generation retired; frontier agents handle answer generation |
| Model calls avoided | n/a | 3 | n/a | Retrieve-only suite |

No speedup claim is made. The after numbers measure added cockpit overhead plus confidence, trace, rerank, and context assembly.
