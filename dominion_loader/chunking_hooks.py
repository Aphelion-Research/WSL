"""Chunking hooks layer for dominion_loader.

Provides a hook registration mechanism so Agent 2 can register alternate
chunking strategies without touching the loader core.

Default strategy: delegate to RAGD (via /index endpoint).
Agent 2 may register per-language chunkers via register_chunker().

Feature flag: DOMINION_CHUNKER_HOOKS=off → always use default RAGD path.

INTERFACE(agent-1): register_chunker, chunker_for  (Agent 2 registers on top)
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterator, Optional


@dataclass(frozen=True)
class Chunk:
    """A document chunk as produced by a chunker strategy.

    INTERFACE(agent-1): stable, consumed by Agent 2's retrieval brain.
    """
    document_id: str
    chunk_id: str
    content: str
    line_start: int
    line_end: int
    language: str
    chunk_type: str      # "function" | "class" | "method" | "section" | "block"
    symbol_name: str


# Chunker function signature: takes (LoadedFile, content: bytes) → Iterator[Chunk]
ChunkerFn = Callable[[Any, bytes], Iterator[Chunk]]

# Registry: language → ChunkerFn
_REGISTRY: Dict[str, ChunkerFn] = {}
_HOOKS_ENABLED = True


def register_chunker(language: str, fn: ChunkerFn) -> None:
    """Register a chunking strategy for a language.

    If DOMINION_CHUNKER_HOOKS=off, registration is accepted but never called.
    """
    _REGISTRY[language.lower()] = fn


def chunker_for(language: str) -> Optional[ChunkerFn]:
    """Return the registered chunker for a language, or None (use RAGD default)."""
    if os.environ.get("DOMINION_CHUNKER_HOOKS", "on").lower() == "off":
        return None
    return _REGISTRY.get(language.lower())


def list_registered() -> list[str]:
    """List languages with registered chunkers."""
    return list(_REGISTRY.keys())


def clear_registry() -> None:
    """Clear all registered chunkers (for testing)."""
    _REGISTRY.clear()
