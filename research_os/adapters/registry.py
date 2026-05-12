from __future__ import annotations

from .base import FetchAdapter, FetchConfig
from .browser_adapter import BrowserAdapter
from .requests_adapter import RequestsAdapter


def available_adapters() -> dict[str, FetchAdapter]:
    return {"requests": RequestsAdapter(), "browser": BrowserAdapter()}


def resolve_adapter(name: str) -> FetchAdapter | None:
    return available_adapters().get(name)


def default_config() -> FetchConfig:
    return FetchConfig()

