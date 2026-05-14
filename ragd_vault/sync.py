from __future__ import annotations

from pathlib import Path

from .builder import build_vault


def sync_vault(vault_root: Path | None = None, *, ragd_db: Path | None = None) -> dict:
    return build_vault(vault_root, ragd_db=ragd_db, wipe=False)
