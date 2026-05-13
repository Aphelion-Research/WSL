"""Semantic diff classifier for dominion_loader (S04).

Classifies the delta between two versions of a file as one of:
  "format-only"    — only formatting changed (indentation, blank lines, line endings)
  "comment-only"   — only comments/docstrings changed
  "whitespace-only"— only whitespace within lines changed (subset of format-only)
  "functional"     — actual logic/structure changed

Conservative bias: when in doubt → "functional" (never miss a real change).

INTERFACE(agent-1): semantic_diff(old, new) -> DiffClass  (consumed by Agent 2)
"""
from __future__ import annotations

import re
from typing import Literal

DiffClass = Literal["format-only", "comment-only", "whitespace-only", "functional"]

# Comment patterns for supported languages
_COMMENT_RE = re.compile(
    r"""
    (?:
        \#[^\n]*                         # Python/shell/YAML single-line (no dotall needed)
      | //[^\n]*                         # C/C++/JS/TS/Go single-line (no dotall needed)
      | /\*.*?\*/                        # C/C++/JS block comment (non-greedy)
      | \"\"\".*?\"\"\"                  # Python triple-double docstring
      | \'\'\'.*?\'\'\'                  # Python triple-single docstring
    )
    """,
    re.VERBOSE | re.DOTALL,
)

_TRAILING_WS = re.compile(r"[ \t]+$", re.MULTILINE)
_BLANK_LINES = re.compile(r"\n\s*\n")
_LEADING_WS = re.compile(r"^[ \t]+", re.MULTILINE)


def semantic_diff(old: bytes, new: bytes) -> DiffClass:
    """Classify the semantic difference between old and new file content.

    Conservative: returns "functional" when uncertain.

    Approach:
    1. If byte-identical → "format-only" (degenerate: no change at all)
    2. If whitespace-normalized versions are identical → "whitespace-only"
    3. If format-normalized versions are identical → "format-only"
    4. If comment-stripped, format-normalized versions are identical → "comment-only"
    5. Otherwise → "functional"
    """
    if old == new:
        return "format-only"  # identical bytes

    try:
        old_text = old.decode("utf-8", errors="replace")
        new_text = new.decode("utf-8", errors="replace")
    except Exception:
        return "functional"  # can't decode → conservative

    # Step 1: whitespace-only (within lines, not structural)
    if _strip_internal_whitespace(old_text) == _strip_internal_whitespace(new_text):
        return "whitespace-only"

    # Step 2: format-only (indentation + blank lines)
    if _normalize_format(old_text) == _normalize_format(new_text):
        return "format-only"

    # Step 3: comment-only (strip comments + format-normalize)
    old_stripped = _normalize_format(_strip_comments(old_text))
    new_stripped = _normalize_format(_strip_comments(new_text))
    if old_stripped == new_stripped:
        return "comment-only"

    return "functional"


# ---------------------------------------------------------------------------
# Internal normalization helpers
# ---------------------------------------------------------------------------
def _strip_internal_whitespace(text: str) -> str:
    """Remove trailing whitespace per line, normalize line endings."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return _TRAILING_WS.sub("", text).strip()


def _normalize_format(text: str) -> str:
    """Remove all indentation, trailing whitespace, and collapse blank lines."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _LEADING_WS.sub("", text)
    text = _TRAILING_WS.sub("", text)
    text = _BLANK_LINES.sub("\n", text)
    return text.strip()


def _strip_comments(text: str) -> str:
    """Remove comment blocks from text. Conservative: may miss exotic comment styles."""
    return _COMMENT_RE.sub("", text)
