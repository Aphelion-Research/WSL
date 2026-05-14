# Dominion Agent OS — Complexity Budgets

Package complexity is scored automatically. Any package over budget triggers warnings in `agent complexity report`.

## Scoring Formula

```
score = (file_count × 1.5)
      + (public_symbols × 0.3)
      + (cli_commands × 2.0)
      - (test_count × 1.0)      ← tests reduce score (good)
      + (todos × 2.5)
      + (temp_adapters × 5.0)   ← TEMP_ADAPTER comments are technical debt
      + (broad_excepts × 1.5)   ← broad `except Exception:` hides errors
      + (untested_modules × 3.0)
      + large_file_penalty       ← files > 300 lines each add 1.0
```

## Budgets

| Package         | Budget |
|-----------------|--------|
| `dominion_loader` | 40    |
| `dominion_ai`     | 50    |
| `dominion_agent`  | 60    |
| `ragd_embed`      | 45    |
| `ragd_hnsw`       | 45    |
| `ragd_chunker`    | 45    |
| `ragd_graph`      | 45    |
| `ragd_vault`      | 45    |
| `ragd`            | 80    |
| `domdata`         | 35    |
| `research_os`     | 50    |
| `scripts`         | 55    |
| `tests`           | 20    |

## What To Do When Over Budget

1. **TEMP_ADAPTER** (×5.0): Search for `TEMP_ADAPTER` comments and resolve them. These are placeholder adapters that should be refactored.
2. **broad_except** (×1.5): Replace `except Exception:` with specific exception types.
3. **untested_modules** (×3.0): Add tests for untested modules.
4. **todos** (×2.5): Resolve or remove TODO/FIXME/HACK comments.
5. **large_files** (×1.0/file): Refactor large files (>300 lines) by extracting logic.

## Check Budget

```bash
# Full report across all packages
python scripts/dominion_cli.py agent complexity report --json

# Single package detail
python scripts/dominion_cli.py agent complexity budget --package dominion_loader --json
```
