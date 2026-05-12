from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..models import FetchResult, Source


@dataclass(frozen=True)
class FetchConfig:
    timeout_s: float = 15.0
    user_agent: str = "DominionResearchOS/0.2"


class FetchAdapter(Protocol):
    name: str

    def fetch(self, url: str, source: Source, config: FetchConfig) -> FetchResult: ...

