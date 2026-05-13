"""Tests for RAGD bridge — skips when RAGD unavailable (use -k 'not integration').

Note: RagdBridge uses urllib (stdlib), NOT requests. Mocks target urlopen.
"""
from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import URLError

import pytest

from dominion_loader.obs import _NullTracer, set_tracer
from dominion_loader.ragd_bridge import IngestResult, RagdBridge


@pytest.fixture(autouse=True)
def null_tracer():
    set_tracer(_NullTracer())


def _mock_urlopen(data: dict, status: int = 200):
    """Build a mock context-manager response for urllib.request.urlopen."""
    mock_resp = MagicMock()
    mock_resp.status = status
    mock_resp.read.return_value = json.dumps(data).encode("utf-8")
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


# ---------------------------------------------------------------------------
# Unit: mock HTTP via urllib
# ---------------------------------------------------------------------------
def test_ingest_paths_empty_list() -> None:
    """Ingesting empty list returns immediately with zero stats."""
    bridge = RagdBridge()
    result = bridge.ingest_paths([])
    assert result.paths_submitted == 0
    assert result.ok is True


def test_bridge_disabled_returns_no_op(monkeypatch) -> None:
    monkeypatch.setenv("DOMINION_RAGD_BRIDGE", "off")
    bridge = RagdBridge()
    result = bridge.ingest_paths(["/some/path.py"])
    assert result.paths_submitted == 1
    assert result.error is not None


def test_health_mock_ok() -> None:
    """Mock the urllib call to test health() parsing."""
    bridge = RagdBridge()
    mock_resp = _mock_urlopen({"status": "ok", "active_chunks": 42})
    with patch("dominion_loader.ragd_bridge.urlopen", return_value=mock_resp):
        result = bridge.health()
    assert result["ok"] is True


def test_health_mock_down() -> None:
    bridge = RagdBridge()
    with patch("dominion_loader.ragd_bridge.urlopen", side_effect=URLError("Connection refused")):
        result = bridge.health()
    assert result["ok"] is False
    assert "error" in result


def test_ingest_paths_mock_success(tmp_path: Path) -> None:
    """Mock a successful /index POST and verify result."""
    path1 = str(tmp_path / "a.py")
    (tmp_path / "a.py").write_text("x = 1\n")

    bridge = RagdBridge()
    mock_resp = _mock_urlopen({"chunks_indexed": 3, "already_current": 0})

    with patch("dominion_loader.ragd_bridge.urlopen", return_value=mock_resp):
        result = bridge.ingest_paths([path1])

    assert result.paths_submitted == 1
    assert result.ok is True
    assert result.chunks_indexed == 3


def test_ingest_paths_mock_connection_error(tmp_path: Path) -> None:
    """Connection error → error field is set."""
    path1 = str(tmp_path / "b.py")
    (tmp_path / "b.py").write_text("y = 2\n")

    bridge = RagdBridge(max_retries=0)

    with patch("dominion_loader.ragd_bridge.urlopen", side_effect=URLError("refused")):
        result = bridge.ingest_paths([path1])

    assert result.ok is False
    assert result.error is not None


def test_ingest_batching(tmp_path: Path) -> None:
    """Large list of paths is split into batches."""
    paths = [str(tmp_path / f"file_{i}.py") for i in range(150)]
    for p in paths:
        Path(p).write_text("x = 1\n")

    bridge = RagdBridge(batch_size=50)
    call_count = [0]

    def fake_urlopen(req, timeout=None):
        call_count[0] += 1
        return _mock_urlopen({"chunks_indexed": 5})

    with patch("dominion_loader.ragd_bridge.urlopen", side_effect=fake_urlopen):
        result = bridge.ingest_paths(paths)

    # 150 paths / 50 batch_size = 3 batches
    assert call_count[0] == 3
    assert result.paths_submitted == 150


def test_ingest_result_base_url() -> None:
    """Bridge stores the URL for diagnostics."""
    bridge = RagdBridge(ragd_url="http://127.0.0.1:7474")
    assert "7474" in bridge._url


def test_ingest_result_elapsed_s() -> None:
    """elapsed_s is derived from duration_ms."""
    r = IngestResult(paths_submitted=1, chunks_indexed=0, already_current=0, duration_ms=500.0, error=None)
    assert abs(r.elapsed_s - 0.5) < 1e-9


# ---------------------------------------------------------------------------
# Integration: requires live RAGD
# ---------------------------------------------------------------------------
@pytest.mark.integration
def test_integration_health_check() -> None:
    """Requires live RAGD at http://127.0.0.1:7474."""
    bridge = RagdBridge()
    result = bridge.health()
    assert result["ok"] is True


@pytest.mark.integration
def test_integration_ingest_single_file(tmp_path: Path) -> None:
    """Requires live RAGD — ingests one real file."""
    f = tmp_path / "test.py"
    f.write_text("# Integration test\ndef foo(): pass\n")

    bridge = RagdBridge()
    result = bridge.ingest_paths([str(f)])
    assert result.paths_submitted == 1
    assert result.ok is True
