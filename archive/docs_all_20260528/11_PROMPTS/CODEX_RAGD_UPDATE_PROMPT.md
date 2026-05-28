---
doc_type: prompt
system: Dominion
ragd_priority: 6
audience:
  - ai_agent
status: current
last_reviewed: 2026-05-19
tags:
  - prompt
  - ragd
  - indexing
---

# CODEX RAGD Update Prompt

**Use Case:** Rebuild RAGD index  
**Complexity:** Low  
**Duration:** 5-10 minutes

---

## Context

RAGD index needs rebuild after:
- New docs added
- Code changes (new modules, functions)
- Stale chunks detected
- Manual request

Repository: `/home/Martin/Dominion`

---

## Mission

Rebuild RAGD index for fresh retrieval.

---

## Workflow

### Step 1: Check Current State (1 min)

```bash
curl http://127.0.0.1:7474/health
```

Expected output:
```json
{
  "status": "ok",
  "uptime_seconds": 3600,
  "total_chunks": 8760,
  "active_chunks": 7159
}
```

### Step 2: Dry-Run Scan (1 min)

```bash
python scripts/dominion_cli.py scan --dry-run --json
```

Check:
- Files to scan count
- Expected new chunks
- No errors

### Step 3: Run Scan (2-3 min)

```bash
python scripts/dominion_cli.py scan
```

Watch for:
- Chunks added/updated count
- Errors (should be none)
- Duration (usually <10s)

### Step 4: Validate Index (2 min)

```bash
# Check new chunk count
curl http://127.0.0.1:7474/health | jq '.active_chunks'

# Test retrieval
python scripts/dominion_cli.py search "recent changes" --top-k 3 --json
```

Should return recently updated docs.

### Step 5: Spot Check (2 min)

Query specific recent additions:

```bash
python scripts/dominion_cli.py search "[new doc topic]" --top-k 5
python scripts/dominion_cli.py search "[new function name]" --top-k 5
```

Verify results include new content.

---

## Validation

RAGD index updated when:
- [ ] Scan completes without errors
- [ ] Active chunks count increased (or same if no changes)
- [ ] Test queries return fresh content
- [ ] Health check shows status="ok"

---

## Output

Brief confirmation:
```
RAGD index rebuilt:
- Scanned: XX files
- Chunks added: +XX
- Chunks updated: XX
- Active chunks: XX total
- Validation: PASS
```

---

## Troubleshooting

**RAGD daemon down:**
```bash
# Check process
ps aux | grep ragd

# Restart if needed
pkill ragd
ragd/build/ragd --db data/ragd.db --host 127.0.0.1 --port 7474 --daemon
```

**Scan fails:**
```bash
# Check logs
tail -100 logs/dominion_scan.log

# Common issues:
# - Permission denied: chmod +x scripts/dominion_cli.py
# - Import error: source .venv/bin/activate
# - RAGD unreachable: check health endpoint
```

---

## Related Prompts

- [[CODEX_DOC_UPDATE_PROMPT]] — Update docs then rebuild index
- [[CODEX_HEALTH_CHECK_PROMPT]] — Validate RAGD health

---

## Retrieval Hints

- "rebuild ragd"
- "ragd index"
- "ragd scan"
