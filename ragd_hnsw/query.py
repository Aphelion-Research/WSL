from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from typing import Any

import numpy as np

from ragd_embed.cache import EmbeddingCache
from ragd_embed.config import load_config
from ragd_embed.pipeline import provider_from_config

from .config import default_index_path
from .index import HNSWIndex


def _query_embedding(query: str) -> list[float]:
    cfg = load_config(require_key=True)
    cache = EmbeddingCache(cfg.cache_path)
    query_hash = "query:" + hashlib.sha256(query.encode("utf-8")).hexdigest()
    cached = cache.get(query_hash, provider=cfg.provider, model=cfg.model, dim=cfg.dim)
    if cached is not None:
        return cached
    provider = provider_from_config(cfg)
    vector = provider.embed_batch([query])[0]
    cache.put(query_hash, vector, provider=cfg.provider, model=cfg.model)
    return vector


def _fetch_chunks(db_path: Path, pairs: list[tuple[int, float]]) -> list[dict[str, Any]]:
    if not pairs or not db_path.exists():
        return []
    distances = {chunk_id: distance for chunk_id, distance in pairs}
    ids = [chunk_id for chunk_id, _ in pairs]
    placeholders = ",".join("?" for _ in ids)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(f"SELECT * FROM chunks WHERE id IN ({placeholders}) AND status='active'", ids).fetchall()
    finally:
        conn.close()
    results: list[dict[str, Any]] = []
    by_id = {int(row["id"]): row for row in rows}
    for rank, chunk_id in enumerate(ids, start=1):
        row = by_id.get(chunk_id)
        if row is None:
            continue
        data = dict(row)
        distance = distances[chunk_id]
        score = max(0.0, 1.0 - float(distance))
        data.update({"chunk_id": chunk_id, "vector_score": score, "score": score, "rank": rank})
        results.append(data)
    return results


def semantic_query(query: str, *, top_k: int = 20, ragd_db_path: Path | None = None, index_path: Path | None = None) -> dict[str, Any]:
    cfg = load_config(require_key=True)
    path = index_path or default_index_path(cfg.provider, cfg.model, cfg.dim)
    index = HNSWIndex(cfg.dim, path)
    index.load()
    vector = np.asarray(_query_embedding(query), dtype=np.float32)
    pairs = index.query(vector, top_k=top_k)
    db_path = Path(ragd_db_path or cfg.ragd_db_path)
    return {"ok": True, "query": query, "top_k": top_k, "results": _fetch_chunks(db_path, pairs), "index": index.stats()}
