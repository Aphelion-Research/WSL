from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Callable, Sequence

from .providers import EmbedProvider

logger = logging.getLogger(__name__)


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

    def _embed_with_split(self, batch: list[str]) -> list[list[float]]:
        """Embed batch, splitting in half on 400 errors."""
        try:
            return self.provider.embed_batch(batch)
        except Exception as exc:
            if "400" in str(exc) and len(batch) > 1:
                logger.warning(f"400 error on batch of {len(batch)}, splitting in half")
                mid = len(batch) // 2
                left = self._embed_with_split(batch[:mid])
                right = self._embed_with_split(batch[mid:])
                return left + right
            raise

    def embed_in_batches(
        self,
        texts: list[str],
        batch_callback: Callable[[int, int], None] | None = None,
    ) -> list[list[float]]:
        vectors: list[list[float]] = []
        retries = 0
        batches = 0
        for batch_idx, start in enumerate(range(0, len(texts), self.batch_size)):
            batch = texts[start:start + self.batch_size]
            attempt = 0
            while True:
                try:
                    batch_vectors = self._embed_with_split(batch)
                    vectors.extend(batch_vectors)
                    batches += 1
                    logger.debug(f"Batch {batch_idx + 1}: embedded {len(batch)} texts → {len(batch_vectors)} vectors")
                    if batch_callback:
                        batch_callback(batch_idx, len(batch))
                    break
                except Exception as exc:
                    if "400" in str(exc):
                        logger.error(f"Batch {batch_idx + 1} got 400 after splits, skipping")
                        raise
                    if attempt >= len(self.retry_delays):
                        logger.error(f"Batch {batch_idx + 1} failed after {attempt} retries: {exc}")
                        raise
                    delay = self.retry_delays[attempt]
                    logger.warning(f"Batch {batch_idx + 1} failed (attempt {attempt + 1}), retrying in {delay}s: {exc}")
                    time.sleep(delay)
                    retries += 1
                    attempt += 1
        self.last_stats = BatchStats(batches=batches, texts=len(texts), retries=retries)
        return vectors
