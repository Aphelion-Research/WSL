from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Sequence

from .providers import EmbedProvider


@dataclass(frozen=True)
class BatchStats:
    batches: int
    texts: int
    retries: int


class EmbedBatcher:
    def __init__(self, provider: EmbedProvider, *, batch_size: int = 128, retry_delays: Sequence[float] = (2.0, 4.0, 8.0)) -> None:
        self.provider = provider
        self.batch_size = max(1, min(int(batch_size), 128))
        self.retry_delays = tuple(retry_delays)
        self.last_stats = BatchStats(0, 0, 0)

    def embed_in_batches(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        retries = 0
        batches = 0
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start:start + self.batch_size]
            attempt = 0
            while True:
                try:
                    vectors.extend(self.provider.embed_batch(batch))
                    batches += 1
                    break
                except Exception:
                    if attempt >= len(self.retry_delays):
                        raise
                    time.sleep(self.retry_delays[attempt])
                    retries += 1
                    attempt += 1
        self.last_stats = BatchStats(batches=batches, texts=len(texts), retries=retries)
        return vectors
