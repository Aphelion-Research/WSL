"""Contract test: LoadedFile interface stability — Agent 2 depends on this."""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from dominion_loader.scan import LoadedFile, iter_loaded_files
from dominion_loader.manifest import Manifest
from dominion_loader.obs import _NullTracer, set_tracer


@pytest.fixture(autouse=True)
def null_tracer():
    set_tracer(_NullTracer())


@pytest.fixture
def small_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "main.py").write_text("def main(): pass\n")
    (repo / "README.md").write_text("# Test\n")
    return repo


def test_loaded_file_has_required_fields(small_repo: Path, tmp_path: Path) -> None:
    """Every LoadedFile must expose the stable Agent 2 interface."""
    db = tmp_path / "manifest.db"
    m = Manifest(db)
    files = list(iter_loaded_files(small_repo, manifest=m))
    assert len(files) >= 2
    for lf in files:
        # Required identity fields
        assert hasattr(lf, "document_id") and lf.document_id
        assert hasattr(lf, "relative_path") and lf.relative_path
        assert hasattr(lf, "path")          # absolute path (as str)
        assert hasattr(lf, "repo_root")
        # Classification
        assert hasattr(lf, "file_class") and lf.file_class
        assert hasattr(lf, "language")
        # Content addressing
        assert hasattr(lf, "content_hash") and lf.content_hash
        # Timing
        assert hasattr(lf, "mtime_ns") and lf.mtime_ns > 0
        assert hasattr(lf, "size") and lf.size >= 0
        # Change status
        assert hasattr(lf, "is_new")
        assert hasattr(lf, "is_changed")
        assert isinstance(lf.is_new, bool)
        assert isinstance(lf.is_changed, bool)
        # trace_id present
        assert hasattr(lf, "trace_id")
    m.close()


def test_loaded_file_is_frozen(small_repo: Path, tmp_path: Path) -> None:
    """LoadedFile must be immutable (frozen dataclass)."""
    db = tmp_path / "manifest.db"
    m = Manifest(db)
    files = list(iter_loaded_files(small_repo, manifest=m))
    lf = files[0]
    with pytest.raises((AttributeError, TypeError)):
        lf.document_id = "mutated"  # type: ignore[misc]
    m.close()


def test_document_id_stable_across_scans(small_repo: Path, tmp_path: Path) -> None:
    """Same file must have same document_id on repeated scans."""
    db = tmp_path / "manifest.db"
    m = Manifest(db)

    files1 = {lf.relative_path: lf.document_id for lf in iter_loaded_files(small_repo, manifest=m)}
    files2 = {lf.relative_path: lf.document_id for lf in iter_loaded_files(small_repo, manifest=m)}

    for path, doc_id in files1.items():
        assert files2[path] == doc_id, f"document_id changed for {path}"
    m.close()


def test_relative_path_is_relative(small_repo: Path, tmp_path: Path) -> None:
    """relative_path must not start with /."""
    db = tmp_path / "manifest.db"
    m = Manifest(db)
    for lf in iter_loaded_files(small_repo, manifest=m):
        assert not lf.relative_path.startswith("/"), f"Not relative: {lf.relative_path}"
    m.close()


def test_absolute_path_resolves(small_repo: Path, tmp_path: Path) -> None:
    """path must point to an existing file."""
    db = tmp_path / "manifest.db"
    m = Manifest(db)
    for lf in iter_loaded_files(small_repo, manifest=m):
        assert Path(lf.path).exists(), f"Missing: {lf.path}"
    m.close()


def test_first_scan_all_files_are_new(small_repo: Path, tmp_path: Path) -> None:
    """On first scan with empty manifest, is_new=True and is_changed=False."""
    db = tmp_path / "manifest.db"
    m = Manifest(db)
    files = list(iter_loaded_files(small_repo, manifest=m))
    for lf in files:
        assert lf.is_new is True
        assert lf.is_changed is False
    m.close()


def test_second_scan_unchanged_files_are_not_new(small_repo: Path, tmp_path: Path) -> None:
    """On rescan with loaded manifest, existing files have is_new=False."""
    from dominion_loader.scan import scan
    db = tmp_path / "manifest.db"
    m = Manifest(db)
    # First scan populates manifest
    scan(small_repo, manifest=m)
    # Second scan via iter_loaded_files
    files = list(iter_loaded_files(small_repo, manifest=m))
    for lf in files:
        assert lf.is_new is False
        assert lf.is_changed is False
    m.close()
