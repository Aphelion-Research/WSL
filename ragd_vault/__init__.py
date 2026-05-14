"""Obsidian vault generator backed by RAGD."""

from .builder import build_vault
from .sync import sync_vault

__all__ = ["build_vault", "sync_vault"]
