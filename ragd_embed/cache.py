from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import numpy as np

from .config import load_config


class EmbeddingCache:
    def __init__(self, path: Path | None = None) -> None:
        cfg = load_config(require_key=False)
        self.path = Path(path or cfg.cache_path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS embedding_cache(
                content_hash TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                dim INTEGER NOT NULL,
                vector BLOB NOT NULL,
                cached_at INTEGER NOT NULL,
                token_count INTEGER
            )
            """
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def get(self, content_hash: str, *, provider: str, model: str, dim: int) -> list[float] | None:
        row = self.conn.execute(
            "SELECT vector, provider, model, dim FROM embedding_cache WHERE content_hash=?",
            (content_hash,),
        ).fetchone()
        if not row or row[1] != provider or row[2] != model or int(row[3]) != dim:
            return None
        vector = np.frombuffer(row[0], dtype=np.float32)
        return vector.astype(float).tolist()

    def put(self, content_hash: str, vector: list[float], *, provider: str, model: str, token_count: int | None = None) -> None:
        array = np.asarray(vector, dtype=np.float32)
        self.conn.execute(
            """
            INSERT OR REPLACE INTO embedding_cache(content_hash, provider, model, dim, vector, cached_at, token_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (content_hash, provider, model, int(array.shape[0]), array.tobytes(), int(time.time()), token_count),
        )
        self.conn.commit()

    def stats(self) -> dict[str, int | str | float]:
        row = self.conn.execute("SELECT COUNT(*), COALESCE(SUM(length(vector)),0) FROM embedding_cache").fetchone()
        providers = self.conn.execute("SELECT provider, model, dim, COUNT(*) FROM embedding_cache GROUP BY provider, model, dim").fetchall()
        return {
            "path": str(self.path),
            "entries": int(row[0]),
            "bytes": int(row[1]),
            "profiles": [{"provider": p, "model": m, "dim": int(d), "entries": int(n)} for p, m, d, n in providers],
        }
