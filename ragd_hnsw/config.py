from __future__ import annotations

import re
from pathlib import Path


def _safe(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def default_index_path(provider: str, model: str, dim: int) -> Path:
    return Path.home() / ".ragd" / f"hnsw_{_safe(provider)}_{_safe(model)}_{dim}.bin"
