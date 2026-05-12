# Local LLM Layer

Dominion V2 uses `local_llm` as an optional Ollama-compatible analyst layer. It is safe to run when Ollama is missing; commands return a disabled status instead of crashing.

## Commands

```bash
llm doctor
llm list
llm summarize FILE_OR_TEXT
llm tag FILE_OR_TEXT
llm claims FILE_OR_TEXT
llm query-expand "research query"
```

## Environment

- `OLLAMA_HOST`: defaults to `http://127.0.0.1:11434`.
- `DOMINION_LLM_MODEL`: defaults to `qwen2.5:3b`.
- `DOMINION_EMBED_MODEL`: defaults to `nomic-embed-text`.

## Manual Model Setup

Dominion does not install large models automatically.

```bash
ollama pull qwen2.5:3b
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

## Safety

Local LLM output is advisory. It should summarize, tag, extract claims, and expand queries, but it should not authorize trading, expose secrets, or replace provenance-backed research.
