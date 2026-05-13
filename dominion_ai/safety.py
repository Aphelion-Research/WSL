from __future__ import annotations

from pathlib import Path


def is_secret_path(filepath: str) -> bool:
    parts = {part.lower() for part in Path(filepath).parts}
    return "secrets" in parts


def redact_path(filepath: str) -> str:
    return "[REDACTED_SECRET_PATH]" if is_secret_path(filepath) else filepath


def redact_secret_mentions(text: str) -> str:
    return text.replace("secrets/", "[REDACTED_SECRET_DIR]/").replace("/secrets", "/[REDACTED_SECRET_DIR]")
