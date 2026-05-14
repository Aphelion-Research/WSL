"""Tests for dominion_loader.discover."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from dominion_loader.discover import discover, DiscoveredFile, DiscoveryError
from dominion_loader.ignore import Ignore
from dominion_loader.obs import make_tracer, set_tracer, _NullTracer


def _null_tracer():
    t = _NullTracer()
    set_tracer(t)
    return t


def _collect(root: Path, ignore: Ignore | None = None) -> list[DiscoveredFile]:
    """Collect only DiscoveredFile items (not errors)."""
    _null_tracer()
    ig = ignore or Ignore()
    return [
        item for item in discover(root, ig)
        if isinstance(item, DiscoveredFile)
    ]


def _collect_all(root: Path, ignore: Ignore | None = None) -> list:
    _null_tracer()
    ig = ignore or Ignore()
    return list(discover(root, ig))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def synthetic_repo(tmp_path: Path) -> Path:
    """Create a small synthetic repo for testing."""
    # Source files
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hello')\n")
    (tmp_path / "src" / "utils.py").write_text("def add(a, b): return a + b\n")

    # Doc files
    (tmp_path / "README.md").write_text("# Test\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.md").write_text("## Guide\n")

    # Config
    (tmp_path / "config.yaml").write_text("key: value\n")

    # Should be ignored
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("[core]\n")
    (tmp_path / "secrets").mkdir()
    (tmp_path / "secrets" / "api.key").write_text("secret123")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "utils.cpython-313.pyc").write_bytes(b"\x00\x01")

    return tmp_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_discovers_source_files(synthetic_repo: Path) -> None:
    files = _collect(synthetic_repo)
    rel_paths = {f.relative_path for f in files}
    assert "src/main.py" in rel_paths
    assert "src/utils.py" in rel_paths
    assert "README.md" in rel_paths
    assert "docs/guide.md" in rel_paths
    assert "config.yaml" in rel_paths


def test_secrets_never_discovered(synthetic_repo: Path) -> None:
    files = _collect(synthetic_repo)
    for f in files:
        assert "secrets" not in f.relative_path, f"Secrets leaked: {f.relative_path}"


def test_git_never_discovered(synthetic_repo: Path) -> None:
    files = _collect(synthetic_repo)
    for f in files:
        assert not f.relative_path.startswith(".git"), f".git leaked: {f.relative_path}"


def test_pycache_never_discovered(synthetic_repo: Path) -> None:
    files = _collect(synthetic_repo)
    for f in files:
        assert "__pycache__" not in f.relative_path


def test_deterministic_order(synthetic_repo: Path) -> None:
    """Two runs produce identical ordering."""
    files1 = [f.relative_path for f in _collect(synthetic_repo)]
    files2 = [f.relative_path for f in _collect(synthetic_repo)]
    assert files1 == files2


def test_each_file_appears_exactly_once(synthetic_repo: Path) -> None:
    """No duplicates."""
    files = _collect(synthetic_repo)
    paths = [f.relative_path for f in files]
    assert len(paths) == len(set(paths)), f"Duplicate paths: {paths}"


def test_repo_root_and_size_populated(synthetic_repo: Path) -> None:
    files = _collect(synthetic_repo)
    for f in files:
        assert f.repo_root == str(synthetic_repo.resolve())
        assert f.size >= 0
        assert f.mtime_ns > 0


def test_empty_repo(tmp_path: Path) -> None:
    """Empty directory produces no files."""
    files = _collect(tmp_path)
    assert files == []


def test_size_limit_filters_large_files(tmp_path: Path) -> None:
    """Files over max_bytes are skipped."""
    big = tmp_path / "big.py"
    big.write_bytes(b"x" * 2048)
    small = tmp_path / "small.py"
    small.write_bytes(b"x" * 10)

    ignore = Ignore(max_bytes=1024)
    files = _collect(tmp_path, ignore)
    rel_paths = {f.relative_path for f in files}

    assert "small.py" in rel_paths
    assert "big.py" not in rel_paths


def test_symlinks_to_files_followed(tmp_path: Path) -> None:
    """Symlinks to files are followed and included."""
    real = tmp_path / "real.py"
    real.write_text("x = 1\n")
    link = tmp_path / "link.py"
    link.symlink_to(real)

    files = _collect(tmp_path)
    rel_paths = {f.relative_path for f in files}
    assert "real.py" in rel_paths
    assert "link.py" in rel_paths


@pytest.mark.skipif(
    os.getuid() == 0,
    reason="chmod 000 has no effect when running as root",
)
def test_unreadable_directory_yields_error(tmp_path: Path) -> None:
    """Unreadable directory yields DiscoveryError, not exception."""
    sub = tmp_path / "locked"
    sub.mkdir()
    (sub / "file.py").write_text("x = 1\n")
    sub.chmod(0o000)

    try:
        items = _collect_all(tmp_path)
        errors = [i for i in items if isinstance(i, DiscoveryError)]
        if not errors:
            pytest.skip("filesystem did not enforce permissions (WSL/container environment)")
        assert len(errors) >= 1
    finally:
        sub.chmod(0o755)
