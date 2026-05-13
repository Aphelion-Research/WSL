"""Tests for dominion_loader.hashing — property tests and fast-path correctness."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from dominion_loader.hashing import (
    HashResult,
    PriorEntry,
    chunk_id_for,
    document_id_for,
    hash_file,
)
from dominion_loader.obs import _NullTracer, set_tracer


def setup_function():
    set_tracer(_NullTracer())


# ---------------------------------------------------------------------------
# document_id_for
# ---------------------------------------------------------------------------
def test_document_id_stable() -> None:
    """Same inputs → same document_id."""
    d1 = document_id_for("/home/Martin/Dominion", "dominion_loader/ignore.py")
    d2 = document_id_for("/home/Martin/Dominion", "dominion_loader/ignore.py")
    assert d1 == d2


def test_document_id_different_paths() -> None:
    """Different paths → different document_ids."""
    d1 = document_id_for("/home/Martin/Dominion", "a.py")
    d2 = document_id_for("/home/Martin/Dominion", "b.py")
    assert d1 != d2


def test_document_id_length() -> None:
    """document_id is exactly 16 chars."""
    d = document_id_for("/home/Martin/Dominion", "foo.py")
    assert len(d) == 16


# ---------------------------------------------------------------------------
# chunk_id_for
# ---------------------------------------------------------------------------
def test_chunk_id_stable() -> None:
    """Same inputs → same chunk_id."""
    c1 = chunk_id_for("abcdef1234567890", 10, 20, "deadbeef")
    c2 = chunk_id_for("abcdef1234567890", 10, 20, "deadbeef")
    assert c1 == c2


def test_chunk_id_different_on_content_change() -> None:
    """Changed content_hash → different chunk_id."""
    c1 = chunk_id_for("abcdef1234567890", 10, 20, "hash_a")
    c2 = chunk_id_for("abcdef1234567890", 10, 20, "hash_b")
    assert c1 != c2


def test_chunk_id_length() -> None:
    assert len(chunk_id_for("a" * 16, 1, 2, "h")) == 16


# ---------------------------------------------------------------------------
# hash_file
# ---------------------------------------------------------------------------
def test_hash_file_matches_sha256(tmp_path: Path) -> None:
    """hash_file must match the sha256 reference."""
    content = b"hello dominion\n" * 100
    f = tmp_path / "test.py"
    f.write_bytes(content)

    result = hash_file(f)
    expected = hashlib.sha256(content).hexdigest()
    assert result.content_hash == expected
    assert result.fast_path is False


def test_hash_file_fast_path_on_mtime_size_match(tmp_path: Path) -> None:
    """Fast path is used when mtime+size match prior."""
    content = b"x = 1\n"
    f = tmp_path / "test.py"
    f.write_bytes(content)

    expected_hash = hashlib.sha256(content).hexdigest()
    st = f.stat()
    prior = PriorEntry(
        content_hash=expected_hash,
        mtime_ns=st.st_mtime_ns,
        size=st.st_size,
    )

    result = hash_file(f, prior)
    assert result.fast_path is True
    assert result.content_hash == expected_hash


def test_hash_file_full_hash_on_mtime_mismatch(tmp_path: Path) -> None:
    """If mtime changes, falls through to full hash."""
    f = tmp_path / "test.py"
    f.write_bytes(b"x = 1\n")
    prior = PriorEntry(content_hash="oldstale", mtime_ns=0, size=6)

    result = hash_file(f, prior)
    assert result.fast_path is False
    assert result.content_hash != "oldstale"


def test_hash_file_mutation_changes_hash(tmp_path: Path) -> None:
    """Any byte mutation changes the hash."""
    f = tmp_path / "test.py"
    original = b"x = 1\n"
    f.write_bytes(original)
    h1 = hash_file(f).content_hash

    f.write_bytes(original + b" ")
    h2 = hash_file(f).content_hash

    assert h1 != h2


def test_hash_file_identical_content_same_hash(tmp_path: Path) -> None:
    """Same content in two files → same hash."""
    content = b"def foo(): pass\n"
    f1 = tmp_path / "a.py"
    f2 = tmp_path / "b.py"
    f1.write_bytes(content)
    f2.write_bytes(content)

    assert hash_file(f1).content_hash == hash_file(f2).content_hash


def test_hash_file_force_full_ignores_prior(tmp_path: Path) -> None:
    """force_full=True always reads the file."""
    f = tmp_path / "test.py"
    content = b"y = 2\n"
    f.write_bytes(content)
    st = f.stat()

    expected = hashlib.sha256(content).hexdigest()
    prior = PriorEntry(content_hash="stale_hash", mtime_ns=st.st_mtime_ns, size=st.st_size)

    result = hash_file(f, prior, force_full=True)
    assert result.content_hash == expected
    assert result.fast_path is False


def test_hash_file_env_full_mode(tmp_path: Path, monkeypatch) -> None:
    """DOMINION_HASH=full forces full hash mode."""
    monkeypatch.setenv("DOMINION_HASH", "full")
    f = tmp_path / "test.py"
    content = b"z = 3\n"
    f.write_bytes(content)
    st = f.stat()
    prior = PriorEntry(content_hash="stale", mtime_ns=st.st_mtime_ns, size=st.st_size)

    result = hash_file(f, prior)
    assert result.fast_path is False


def test_hash_file_missing_raises(tmp_path: Path) -> None:
    """Missing file raises OSError."""
    with pytest.raises(OSError):
        hash_file(tmp_path / "nonexistent.py")
