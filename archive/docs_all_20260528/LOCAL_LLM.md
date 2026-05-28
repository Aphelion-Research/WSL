# Local Generation Retired

Dominion no longer ships a local generation subsystem. Claude Code, Codex, and Cursor handle generation; RAGD provides retrieval context.

Use:

```bash
dominion search "query"
dominion ask "query" --json
dominion embed stats
dominion vault status
```

The `llm` wrapper remains only as a compatibility note and does not load models or send code anywhere.
