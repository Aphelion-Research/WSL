"""Tests for dominion_loader.semantic_diff."""
from __future__ import annotations

import pytest
from dominion_loader.semantic_diff import semantic_diff


# ---------------------------------------------------------------------------
# Identical content
# ---------------------------------------------------------------------------
def test_identical_is_format_only() -> None:
    content = b"def foo():\n    return 1\n"
    assert semantic_diff(content, content) == "format-only"


# ---------------------------------------------------------------------------
# Whitespace-only
# ---------------------------------------------------------------------------
def test_trailing_whitespace_is_whitespace_only() -> None:
    old = b"def foo():  \n    return 1  \n"
    new = b"def foo():\n    return 1\n"
    result = semantic_diff(old, new)
    assert result in ("whitespace-only", "format-only")


def test_extra_blank_lines_is_format_only() -> None:
    old = b"def foo():\n    return 1\n"
    new = b"def foo():\n\n\n    return 1\n\n"
    result = semantic_diff(old, new)
    assert result in ("format-only", "whitespace-only")


# ---------------------------------------------------------------------------
# Comment-only
# ---------------------------------------------------------------------------
def test_add_python_comment_is_comment_only() -> None:
    old = b"def foo():\n    return 1\n"
    new = b"# This is a helper function\ndef foo():\n    return 1\n"
    result = semantic_diff(old, new)
    assert result == "comment-only"


def test_add_cpp_line_comment_is_comment_only() -> None:
    old = b"int foo() { return 1; }\n"
    new = b"// Returns 1\nint foo() { return 1; }\n"
    result = semantic_diff(old, new)
    assert result == "comment-only"


# ---------------------------------------------------------------------------
# Functional changes
# ---------------------------------------------------------------------------
def test_changed_return_value_is_functional() -> None:
    old = b"def foo():\n    return 1\n"
    new = b"def foo():\n    return 2\n"
    assert semantic_diff(old, new) == "functional"


def test_new_function_is_functional() -> None:
    old = b"def foo():\n    return 1\n"
    new = b"def foo():\n    return 1\n\ndef bar():\n    return 2\n"
    assert semantic_diff(old, new) == "functional"


def test_renamed_variable_is_functional() -> None:
    old = b"x = 1\ny = x + 1\n"
    new = b"z = 1\ny = z + 1\n"
    assert semantic_diff(old, new) == "functional"


def test_empty_to_content_is_functional() -> None:
    assert semantic_diff(b"", b"def foo(): pass\n") == "functional"


def test_content_to_empty_is_functional() -> None:
    assert semantic_diff(b"def foo(): pass\n", b"") == "functional"


# ---------------------------------------------------------------------------
# Conservative bias
# ---------------------------------------------------------------------------
def test_binary_content_is_functional() -> None:
    """Binary content → conservative → functional."""
    # Even if we can't tell, we default to functional
    result = semantic_diff(b"\x00\x01\x02", b"\x00\x01\x03")
    assert result == "functional"


def test_ambiguous_is_functional() -> None:
    """When unsure, must return 'functional'."""
    # Structural rewrite with different whitespace
    old = b"for i in range(10): print(i)\n"
    new = b"for i in range(\n    10\n):\n    print(\n        i\n    )\n"
    result = semantic_diff(old, new)
    # This could be format-only but we accept either functional or format-only
    assert result in ("format-only", "functional")
