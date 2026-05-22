"""Test CLI status commands with ollama provider (no API key required)."""
from __future__ import annotations

import json
import pytest

from ragd_embed.cli import cmd_doctor, cmd_stats


def test_doctor_ollama_without_key_ok(monkeypatch, tmp_path, capsys):
    """dominion embed doctor should report OK for ollama without API key."""
    monkeypatch.setenv("RAGD_EMBED_PROVIDER", "ollama")
    monkeypatch.delenv("RAGD_EMBED_API_KEY", raising=False)
    monkeypatch.setenv("RAGD_EMBED_CACHE", str(tmp_path / "cache.db"))

    class Args:
        json = True

    exit_code = cmd_doctor(Args())
    out = capsys.readouterr().out
    payload = json.loads(out)

    assert exit_code == 0, "doctor should return 0 for ollama without key"
    assert payload["ok"] is True, "doctor should report ok=True for ollama"
    assert payload["provider"] == "ollama"
    assert payload["api_key_present"] is False
    assert payload["api_key_required"] is False
    assert payload["local_provider"] is True
    assert "error" not in payload, "doctor should not report error for ollama without key"


def test_doctor_openai_without_key_error(monkeypatch, tmp_path, capsys):
    """dominion embed doctor should report ERROR for openai without API key."""
    monkeypatch.setenv("RAGD_EMBED_PROVIDER", "openai")
    monkeypatch.delenv("RAGD_EMBED_API_KEY", raising=False)
    monkeypatch.setenv("RAGD_EMBED_CACHE", str(tmp_path / "cache.db"))

    class Args:
        json = True

    exit_code = cmd_doctor(Args())
    out = capsys.readouterr().out
    payload = json.loads(out)

    assert exit_code == 1, "doctor should return 1 for openai without key"
    assert payload["ok"] is False
    assert payload["provider"] == "openai"
    assert payload["api_key_present"] is False
    assert payload["api_key_required"] is True
    assert payload["local_provider"] is False
    assert "error" in payload
    assert "RAGD_EMBED_API_KEY" in payload["error"]


def test_stats_ollama_without_key(monkeypatch, tmp_path, capsys):
    """dominion embed stats should work for ollama without API key."""
    monkeypatch.setenv("RAGD_EMBED_PROVIDER", "ollama")
    monkeypatch.delenv("RAGD_EMBED_API_KEY", raising=False)
    monkeypatch.setenv("RAGD_EMBED_CACHE", str(tmp_path / "cache.db"))

    class Args:
        json = True

    exit_code = cmd_stats(Args())
    out = capsys.readouterr().out
    payload = json.loads(out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["provider"] == "ollama"
    assert payload["api_key_present"] is False
