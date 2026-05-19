from __future__ import annotations

import hashlib
import logging
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

import numpy as np
from rich.console import Console
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn

from .batcher import EmbedBatcher
from .cache import EmbeddingCache
from .config import EmbedConfig, load_config
from .providers import EmbedProvider
from .providers.bedrock import BedrockProvider
from .providers.openai import OpenAIProvider
from .providers.voyage import VoyageProvider

logger = logging.getLogger(__name__)
console = Console()


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
    if cfg.provider == "bedrock":
        return BedrockProvider(api_key=cfg.api_key, model=cfg.model)
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
    show_progress: bool = True,
) -> EmbedRunStats:
    cfg = cfg or load_config(require_key=True)
    provider = provider or provider_from_config(cfg)
    cache = cache or EmbeddingCache(cfg.cache_path)
    ragd_db_path = Path(ragd_db_path or cfg.ragd_db_path)
    chunk_list = list(chunks) if chunks is not None else load_chunks_from_ragd(ragd_db_path, changed_only=changed_only)

    console.print(f"[bold cyan]Embedding pipeline starting[/bold cyan]")
    console.print(f"Provider: [yellow]{provider.name}[/yellow]  Model: [yellow]{provider.model}[/yellow]  Dim: [yellow]{provider.dim}[/yellow]")
    console.print(f"Chunks found: [green]{len(chunk_list)}[/green]")

    hits = 0
    misses: list[ChunkInput] = []
    vectors_by_id: dict[int, list[float]] = {}

    start_time = time.time()

    if show_progress and chunk_list:
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]Cache check[/bold blue]"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Checking cache", total=len(chunk_list))
            for chunk in chunk_list:
                cached = cache.get(chunk.content_hash, provider=provider.name, model=provider.model, dim=provider.dim)
                if cached is not None:
                    hits += 1
                    vectors_by_id[chunk.chunk_id] = cached
                else:
                    misses.append(chunk)
                progress.update(task, advance=1)
    else:
        for chunk in chunk_list:
            cached = cache.get(chunk.content_hash, provider=provider.name, model=provider.model, dim=provider.dim)
            if cached is not None:
                hits += 1
                vectors_by_id[chunk.chunk_id] = cached
            else:
                misses.append(chunk)

    console.print(f"Cache hits: [green]{hits}[/green]  Cache misses: [red]{len(misses)}[/red]")

    if misses:
        console.print(f"[bold cyan]Embedding {len(misses)} chunks via API[/bold cyan]")
        batcher = EmbedBatcher(provider, batch_size=cfg.batch_size)

        batch_callback: Callable[[int, int], None] | None = None
        if show_progress:
            num_batches = (len(misses) + cfg.batch_size - 1) // cfg.batch_size
            progress = Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]Batch {task.fields[current]}/{task.fields[total_batches]}[/bold blue]"),
                BarColumn(),
                TaskProgressColumn(),
                TextColumn("•"),
                TextColumn("{task.fields[rate]:.1f} emb/s"),
                TextColumn("•"),
                TimeRemainingColumn(),
                console=console,
            )
            progress.start()
            task_id = progress.add_task("Embedding", total=len(misses), current=0, total_batches=num_batches, rate=0.0)

            batch_counter = [0]
            embed_start = [time.time()]

            def callback(batch_idx: int, batch_size: int) -> None:
                batch_counter[0] += 1
                completed = min((batch_idx + 1) * cfg.batch_size, len(misses))
                elapsed = time.time() - embed_start[0]
                rate = completed / elapsed if elapsed > 0 else 0.0
                progress.update(task_id, completed=completed, current=batch_counter[0], total=num_batches, rate=rate)

            batch_callback = callback

        try:
            vectors = batcher.embed_in_batches([chunk_text(chunk) for chunk in misses], batch_callback=batch_callback)
        finally:
            if show_progress:
                progress.stop()

        if len(vectors) != len(misses):
            raise RuntimeError(f"embedding provider returned {len(vectors)} vectors for {len(misses)} chunks")
        for chunk, vector in zip(misses, vectors):
            cache.put(chunk.content_hash, vector, provider=provider.name, model=provider.model)
            vectors_by_id[chunk.chunk_id] = vector
        api_batches = batcher.last_stats.batches

        elapsed = time.time() - start_time
        rate = len(misses) / elapsed if elapsed > 0 else 0.0
        console.print(f"[green]✓[/green] Embedded {len(misses)} chunks in {api_batches} batches ([cyan]{rate:.1f}[/cyan] emb/s)")
        if batcher.last_stats.retries > 0:
            console.print(f"[yellow]⚠[/yellow] Retries: {batcher.last_stats.retries}")
    else:
        api_batches = 0
        console.print("[green]✓[/green] All chunks cached, no API calls needed")

    store_vectors_in_ragd(ragd_db_path, vectors_by_id)
    console.print(f"[green]✓[/green] Stored {len(vectors_by_id)} vectors in ragd_db")

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
