from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .batcher import EmbedBatcher
from .cache import EmbeddingCache
from .config import EmbedConfig, load_config
from .providers import EmbedProvider
from .providers.openai import OpenAIProvider
from .providers.voyage import VoyageProvider


@dataclass(frozen=True)
class ChunkInput:
    chunk_id: int
    content: str
    content_hash: str
    qualified_name: str = ""
    docstring: str = ""


@dataclass(frozen=True)
class EmbedRunStats:
    chunks_seen: int
    cache_hits: int
    cache_misses: int
    api_batches: int
    vectors_stored: int


def provider_from_config(cfg: EmbedConfig) -> EmbedProvider:
    if cfg.provider == "voyage":
        return VoyageProvider(api_key=cfg.api_key, model=cfg.model)
    if cfg.provider == "openai":
        return OpenAIProvider(api_key=cfg.api_key, model=cfg.model)
    raise ValueError(f"unsupported provider: {cfg.provider}")


def chunk_text(chunk: ChunkInput) -> str:
    parts = [chunk.qualified_name, chunk.docstring, chunk.content]
    return "\n".join(part for part in parts if part)


def _hash_content(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def load_chunks_from_ragd(db_path: Path, *, changed_only: bool = False) -> list[ChunkInput]:
    if not db_path.exists():
        return []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(chunks)").fetchall()}
        where = "WHERE status='active'"
        if changed_only and "embedding" in columns:
            where += " AND embedding IS NULL"
        qualified = "qualified_name" if "qualified_name" in columns else "'' AS qualified_name"
        docstring = "docstring" if "docstring" in columns else "'' AS docstring"
        content_hash = "content_hash" if "content_hash" in columns else "'' AS content_hash"
        rows = conn.execute(
            f"SELECT id, content, {content_hash}, {qualified}, {docstring} FROM chunks {where}"
        ).fetchall()
        chunks = []
        for row in rows:
            content = row["content"] or ""
            chunks.append(ChunkInput(
                chunk_id=int(row["id"]),
                content=content,
                content_hash=row["content_hash"] or _hash_content(content),
                qualified_name=row["qualified_name"] or "",
                docstring=row["docstring"] or "",
            ))
        return chunks
    finally:
        conn.close()


def ensure_embedding_column(db_path: Path) -> None:
    if not db_path.exists():
        return
    conn = sqlite3.connect(db_path)
    try:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(chunks)").fetchall()}
        if "embedding" not in columns:
            conn.execute("ALTER TABLE chunks ADD COLUMN embedding BLOB")
            conn.commit()
    finally:
        conn.close()


def store_vectors_in_ragd(db_path: Path, vectors: dict[int, list[float]]) -> None:
    if not db_path.exists() or not vectors:
        return
    ensure_embedding_column(db_path)
    conn = sqlite3.connect(db_path)
    try:
        for chunk_id, vector in vectors.items():
            blob = np.asarray(vector, dtype=np.float32).tobytes()
            conn.execute("UPDATE chunks SET embedding=? WHERE id=?", (blob, int(chunk_id)))
        conn.commit()
    finally:
        conn.close()


def run_embedding_pipeline(
    chunks: Iterable[ChunkInput] | None = None,
    *,
    cfg: EmbedConfig | None = None,
    provider: EmbedProvider | None = None,
    cache: EmbeddingCache | None = None,
    ragd_db_path: Path | None = None,
    changed_only: bool = False,
) -> EmbedRunStats:
    cfg = cfg or load_config(require_key=True)
    provider = provider or provider_from_config(cfg)
    cache = cache or EmbeddingCache(cfg.cache_path)
    ragd_db_path = Path(ragd_db_path or cfg.ragd_db_path)
    chunk_list = list(chunks) if chunks is not None else load_chunks_from_ragd(ragd_db_path, changed_only=changed_only)

    hits = 0
    misses: list[ChunkInput] = []
    vectors_by_id: dict[int, list[float]] = {}
    for chunk in chunk_list:
        cached = cache.get(chunk.content_hash, provider=provider.name, model=provider.model, dim=provider.dim)
        if cached is not None:
            hits += 1
            vectors_by_id[chunk.chunk_id] = cached
        else:
            misses.append(chunk)

    if misses:
        batcher = EmbedBatcher(provider, batch_size=cfg.batch_size)
        vectors = batcher.embed_in_batches([chunk_text(chunk) for chunk in misses])
        if len(vectors) != len(misses):
            raise RuntimeError(f"embedding provider returned {len(vectors)} vectors for {len(misses)} chunks")
        for chunk, vector in zip(misses, vectors):
            cache.put(chunk.content_hash, vector, provider=provider.name, model=provider.model)
            vectors_by_id[chunk.chunk_id] = vector
        api_batches = batcher.last_stats.batches
    else:
        api_batches = 0

    store_vectors_in_ragd(ragd_db_path, vectors_by_id)
    return EmbedRunStats(
        chunks_seen=len(chunk_list),
        cache_hits=hits,
        cache_misses=len(misses),
        api_batches=api_batches,
        vectors_stored=len(vectors_by_id),
    )


def embed_chunks(chunks: list[ChunkInput], storage: Any | None = None) -> int:
    stats = run_embedding_pipeline(chunks, ragd_db_path=Path(storage) if storage else None)
    return stats.api_batches
