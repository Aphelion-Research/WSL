---
synced: 2026-05-19 19:42
---
# Data Pipeline

Raw XAUUSD data:

```text
data/raw/mt5/xauusd/ticks/date=YYYY-MM-DD/ticks-HH.jsonl
data/raw/mt5/xauusd/bars/timeframe=M1/date=YYYY-MM-DD/bars-HH.jsonl
data/raw/mt5/xauusd/health/date=YYYY-MM-DD/health-HH.jsonl
```

Collect:

```bash
domdata collect-xau
domdata collect-status
```

Convert and summarize:

```bash
domdata convert-xau --date $(date -u +%F)
domdata duckdb-init
domdata duckdb-summary --date $(date -u +%F)
```
