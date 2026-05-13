"""Contract test: RAGD ingestion result schema (using mocks).

Note: RagdBridge uses urllib (stdlib), NOT requests. Mocks target urlopen.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import URLError

import pytest

from dominion_loader.ragd_bridge import IngestResult, RagdBridge


def _mock_urlopen(data: dict, status: int = 200):
    mock_resp = MagicMock()
    mock_resp.status = status
    mock_resp.read.return_value = json.dumps(data).encode("utf-8")
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def test_ingest_result_has_required_fields() -> None:
    """IngestResult must expose the contract fields Agent 2 depends on."""
    r = IngestResult(
        paths_submitted=10,
        chunks_indexed=42,
        already_current=3,
        duration_ms=500.0,
        error=None,
    )
    # Required contract fields
    assert hasattr(r, "paths_submitted")
    assert hasattr(r, "chunks_indexed")
    assert hasattr(r, "already_current")
    assert hasattr(r, "duration_ms")
    assert hasattr(r, "error")

    # Derived properties
    assert hasattr(r, "ok")
    assert hasattr(r, "elapsed_s")
    assert hasattr(r, "paths_failed")

    # Types
    assert isinstance(r.paths_submitted, int)
    assert isinstance(r.chunks_indexed, int)
    assert isinstance(r.duration_ms, float)
    assert r.error is None


def test_ingest_result_ok_property() -> None:
    """ok is True when no error."""
    good = IngestResult(paths_submitted=5, chunks_indexed=20, already_current=0, duration_ms=100.0, error=None)
    assert good.ok is True

    bad = IngestResult(paths_submitted=5, chunks_indexed=0, already_current=0, duration_ms=50.0, error="connect failed")
    assert bad.ok is False


def test_ingest_result_elapsed_s() -> None:
    r = IngestResult(paths_submitted=1, chunks_indexed=0, already_current=0, duration_ms=1500.0, error=None)
    assert abs(r.elapsed_s - 1.5) < 1e-9


def test_ingest_result_to_dict_serializable() -> None:
    """IngestResult.to_dict() produces a JSON-serializable dict."""
    r = IngestResult(paths_submitted=3, chunks_indexed=10, already_current=1, duration_ms=300.0, error=None)
    d = r.to_dict()
    assert isinstance(d, dict)
    json.dumps(d)  # must not raise


def test_ingest_result_to_dict_schema() -> None:
    r = IngestResult(paths_submitted=3, chunks_indexed=10, already_current=1, duration_ms=300.0, error=None)
    d = r.to_dict()
    required = {"paths_submitted", "chunks_indexed", "duration_ms", "elapsed_s", "ok", "error"}
    for key in required:
        assert key in d, f"Missing key: {key}"


def test_mock_ingest_returns_correct_schema(tmp_path: Path) -> None:
    """Full ingest contract: result schema is valid."""
    p = str(tmp_path / "file.py")
    (tmp_path / "file.py").write_text("x = 1\n")

    bridge = RagdBridge()
    mock_resp = _mock_urlopen({"chunks_indexed": 5, "already_current": 0})

    with patch("dominion_loader.ragd_bridge.urlopen", return_value=mock_resp):
        result = bridge.ingest_paths([p])

    assert result.paths_submitted == 1
    assert result.ok is True
    assert isinstance(result.elapsed_s, float)
    assert result.elapsed_s >= 0.0


def test_bridge_url_defaults_to_ragd() -> None:
    bridge = RagdBridge()
    assert "7474" in bridge._url


def test_empty_ingest_is_trivially_ok() -> None:
    bridge = RagdBridge()
    result = bridge.ingest_paths([])
    assert result.ok is True
    assert result.paths_submitted == 0
