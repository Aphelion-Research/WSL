"""Tests for dominion_loader.chunking_hooks."""
from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest

from dominion_loader.chunking_hooks import (
    Chunk,
    ChunkerFn,
    clear_registry,
    chunker_for,
    list_registered,
    register_chunker,
)


@pytest.fixture(autouse=True)
def clean_registry():
    """Reset the chunker registry between tests."""
    clear_registry()
    yield
    clear_registry()


def test_register_and_retrieve() -> None:
    def my_chunker(file, content: bytes) -> Iterator[Chunk]:
        return iter([])

    register_chunker("python", my_chunker)
    result = chunker_for("python")
    assert result is my_chunker


def test_chunker_for_unknown_returns_none() -> None:
    assert chunker_for("unknown_language") is None


def test_list_registered_reflects_registry() -> None:
    register_chunker("rust", lambda f, c: iter([]))
    register_chunker("go", lambda f, c: iter([]))
    registered = list_registered()
    assert "rust" in registered
    assert "go" in registered


def test_hooks_disabled_returns_none(monkeypatch) -> None:
    monkeypatch.setenv("DOMINION_CHUNKER_HOOKS", "off")
    register_chunker("python", lambda f, c: iter([]))
    assert chunker_for("python") is None


def test_chunker_called_for_correct_language() -> None:
    calls: list[str] = []

    def py_chunker(file, content: bytes) -> Iterator[Chunk]:
        calls.append("python")
        return iter([])

    register_chunker("python", py_chunker)

    fn = chunker_for("python")
    assert fn is not None
    list(fn(None, b"x = 1\n"))
    assert calls == ["python"]
