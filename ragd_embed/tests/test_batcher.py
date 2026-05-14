from __future__ import annotations

from ragd_embed.batcher import EmbedBatcher


class FlakyProvider:
    name = "fake"
    model = "fake-model"
    dim = 2

    def __init__(self) -> None:
        self.calls = 0

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("rate limit")
        return [[float(len(text)), 0.0] for text in texts]

    def health(self) -> dict:
        return {"ok": True}


def test_batches_split_and_retry():
    provider = FlakyProvider()
    batcher = EmbedBatcher(provider, batch_size=128, retry_delays=(0.0,))
    vectors = batcher.embed_in_batches(["x"] * 129)
    assert len(vectors) == 129
    assert batcher.last_stats.batches == 2
    assert batcher.last_stats.retries == 1
