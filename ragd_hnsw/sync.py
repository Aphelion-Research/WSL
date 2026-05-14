from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ragd_embed.cache import EmbeddingCache

from .index import HNSWIndex


@dataclass(frozen=True)
class SyncStats:
    added: int
    removed: int
    skipped_no_embedding: int
    total_in_index: int


def _active_chunks(ragd_db: Path) -> list[tuple[int, str]]:
    conn = sqlite3.connect(ragd_db)
    try:
        return [(int(row[0]), str(row[1])) for row in conn.execute("SELECT id, content_hash FROM chunks WHERE status='active'").fetchall()]
    finally:
        conn.close()


def sync_index(ragd_db: Path, embed_db: Path, hnsw_index: HNSWIndex) -> SyncStats:
    cache = EmbeddingCache(embed_db)
    active = _active_chunks(Path(ragd_db)) if Path(ragd_db).exists() else []
    previous_ids = set(map(int, hnsw_index._ids))
    ids: list[int] = []
    vectors: list[list[float]] = []
    skipped = 0
    for chunk_id, content_hash in active:
        vector = None
        for row in cache.conn.execute("SELECT provider, model, dim FROM embedding_cache WHERE content_hash=?", (content_hash,)).fetchall():
            vector = cache.get(content_hash, provider=row[0], model=row[1], dim=int(row[2]))
            if vector is not None:
                break
        if vector is None:
            skipped += 1
            continue
        ids.append(chunk_id)
        vectors.append(vector)
    active_ids = set(ids)
    removed = len(previous_ids - active_ids)
    if ids:
        matrix = np.asarray(vectors, dtype=np.float32)
        hnsw_index.build(matrix, np.asarray(ids, dtype=np.int64))
    else:
        hnsw_index.build(np.empty((0, hnsw_index.dim), dtype=np.float32), np.asarray([], dtype=np.int64))
    return SyncStats(added=len(active_ids - previous_ids), removed=removed, skipped_no_embedding=skipped, total_in_index=len(ids))
