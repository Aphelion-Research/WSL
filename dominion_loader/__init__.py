"""dominion_loader — deterministic, observable, measurable file-ingestion foundation.

ASSUMPTION(agent-1): Python 3.13 venv at /home/Martin/Dominion/.venv
ASSUMPTION(agent-1): SQLite ≥ 3.40 with WAL mode
ASSUMPTION(agent-1): DOMINION_ROOT defaults to ~/Dominion
ASSUMPTION(agent-1): RAGD_URL defaults to http://127.0.0.1:7474
"""
from __future__ import annotations

__version__ = "1.0.0"

from dominion_loader.api import (
    LoadedFile,
    ManifestEntry,
    HardwareProfile,
    CacheHit,
    iter_files,
    get_manifest_entry,
    list_changed_since,
    semantic_diff,
    hw_probe,
    cache_get,
    cache_put,
)

__all__ = [
    "LoadedFile",
    "ManifestEntry",
    "HardwareProfile",
    "CacheHit",
    "iter_files",
    "get_manifest_entry",
    "list_changed_since",
    "semantic_diff",
    "hw_probe",
    "cache_get",
    "cache_put",
]
