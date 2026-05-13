"""Tests for dominion_loader.classify."""
from __future__ import annotations

from pathlib import Path

import pytest

from dominion_loader.classify import classify, is_likely_binary


@pytest.mark.parametrize("path,expected_class,expected_lang", [
    ("foo.py",           "code",    "python"),
    ("main.cpp",         "code",    "cpp"),
    ("lib.h",            "code",    "cpp"),
    ("app.rs",           "code",    "rust"),
    ("server.go",        "code",    "go"),
    ("index.ts",         "code",    "typescript"),
    ("app.js",           "code",    "javascript"),
    ("run.sh",           "code",    "shell"),
    ("schema.sql",       "code",    "sql"),
    ("README.md",        "doc",     "markdown"),
    ("AGENTS.md",        "doc",     "markdown"),
    ("notes.rst",        "doc",     "rst"),
    ("notes.txt",        "doc",     "text"),
    ("config.yaml",      "config",  "yaml"),
    ("settings.json",    "config",  "json"),
    ("setup.toml",       "config",  "toml"),
    ("nginx.conf",       "config",  "conf"),
    ("CMakeLists.txt",   "config",  "cmake"),
    ("Makefile",         "config",  "makefile"),
    ("Dockerfile",       "config",  "dockerfile"),
    ("data.csv",         "data",    "csv"),
    ("events.jsonl",     "data",    "jsonl"),
    ("mystery.xyz",      "unknown", "unknown"),
])
def test_classify_extension(path: str, expected_class: str, expected_lang: str) -> None:
    fc, lang = classify(Path(path))
    assert fc == expected_class, f"{path}: expected class {expected_class!r}, got {fc!r}"
    assert lang == expected_lang, f"{path}: expected lang {expected_lang!r}, got {lang!r}"


def test_is_likely_binary_text(tmp_path: Path) -> None:
    f = tmp_path / "text.py"
    f.write_bytes(b"print('hello')\n")
    assert not is_likely_binary(f)


def test_is_likely_binary_null_bytes(tmp_path: Path) -> None:
    f = tmp_path / "binary.bin"
    f.write_bytes(b"\x00\x01\x02\x03" * 100)
    assert is_likely_binary(f)


def test_is_likely_binary_missing() -> None:
    """Missing files are treated as binary (safe default)."""
    assert is_likely_binary(Path("/nonexistent/file.bin"))
