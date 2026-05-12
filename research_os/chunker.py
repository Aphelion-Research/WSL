from __future__ import annotations

import hashlib
import re

from .models import DocumentChunk


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _estimate_tokens(text: str) -> int:
    return max(1, int(len(text.split()) * 1.35))


def _sliding_chunks(text: str, max_words: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    chunks: list[str] = []
    step = max_words
    for start in range(0, len(words), step):
        part = " ".join(words[start : start + max_words]).strip()
        if part:
            chunks.append(part)
    return chunks


def chunk_markdown(markdown: str, max_words: int = 700) -> list[DocumentChunk]:
    sections: list[tuple[str, list[str]]] = []
    current_heading = "Document"
    current_lines: list[str] = []
    in_frontmatter = False
    for line in markdown.splitlines():
        if line.strip() == "---":
            in_frontmatter = not in_frontmatter
            continue
        if in_frontmatter:
            continue
        match = HEADING_RE.match(line)
        if match:
            if current_lines:
                sections.append((current_heading, current_lines))
            current_heading = match.group(2).strip()
            current_lines = [line]
        else:
            current_lines.append(line)
    if current_lines:
        sections.append((current_heading, current_lines))

    output: list[DocumentChunk] = []
    for heading, lines in sections:
        text = "\n".join(lines).strip()
        if not text:
            continue
        pieces = [text] if len(text.split()) <= max_words else _sliding_chunks(text, max_words)
        for piece in pieces:
            output.append(
                DocumentChunk(
                    chunk_index=len(output),
                    heading=heading,
                    content=piece,
                    content_hash=_hash(piece),
                    token_estimate=_estimate_tokens(piece),
                )
            )
    return output
