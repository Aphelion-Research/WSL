from __future__ import annotations

import sqlite3

from ragd_embed.cache import EmbeddingCache
from ragd_hnsw.index import HNSWIndex
from ragd_hnsw.sync import sync_index


def _ragd_db(path):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE chunks(id INTEGER PRIMARY KEY, content_hash TEXT, status TEXT)")
    conn.execute("INSERT INTO chunks(id, content_hash, status) VALUES (1, 'h1', 'active'), (2, 'h2', 'deleted')")
    conn.commit()
    conn.close()


def test_sync_adds_active_and_skips_missing(tmp_path):
    ragd_db = tmp_path / "ragd.db"
    embed_db = tmp_path / "embed.db"
    _ragd_db(ragd_db)
    cache = EmbeddingCache(embed_db)
    cache.put("h1", [1.0, 0.0], provider="voyage", model="voyage-code-2")
    index = HNSWIndex(2, tmp_path / "hnsw.bin")
    stats = sync_index(ragd_db, embed_db, index)
    assert stats.added == 1
    assert stats.total_in_index == 1
    assert index.stats()["element_count"] == 1
