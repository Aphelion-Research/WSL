from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .safety import is_secret_path, redact_secret_mentions
from .types import ScoredChunk


TEMP_ADAPTER_NOTE = "TEMP_ADAPTER(agent-1): RAGD /query omits content_hash and document_id; remove when REST results expose both fields."


class RagdError(RuntimeError):
    pass


class RagdClient:
    def __init__(self, base_url: str | None = None, timeout: float = 10.0):
        self.base_url = (base_url or os.environ.get("RAGD_URL") or "http://127.0.0.1:7474").rstrip("/")
        self.timeout = timeout

    def _request(self, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        req = Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urlopen(req, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
                return json.loads(body) if body else {}
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            raise RagdError(f"RAGD request failed for {url}: {exc}") from exc

    def health(self) -> dict[str, Any]:
        return self._request("/health")

    def query(self, q: str, *, mode: str = "hybrid", top_k: int = 10) -> dict[str, Any]:
        return self._request("/query", {"q": q, "mode": mode, "top_k": top_k})

    def handoff(self) -> dict[str, Any]:
        return self._request("/handoff")

    def decisions(self, *, limit: int = 50) -> dict[str, Any]:
        suffix = urlencode({"limit": limit})
        return self._request(f"/memory/decisions?{suffix}")

    def graph_symbols(self, *, root: str = "", depth: int = 3) -> dict[str, Any]:
        suffix = urlencode({"root": root, "depth": depth})
        return self._request(f"/graph/symbols?{suffix}")


def _content_hash(raw: dict[str, Any]) -> str:
    if raw.get("content_hash"):
        return str(raw["content_hash"])
    identity = f"{raw.get('filepath','')}:{raw.get('line_start',1)}:{raw.get('line_end',1)}:{raw.get('content','')}"
    return hashlib.sha256(identity.encode("utf-8", errors="replace")).hexdigest()[:16]


def parse_chunk(raw: dict[str, Any], *, source: str = "hybrid") -> ScoredChunk | None:
    filepath = str(raw.get("filepath") or "")
    if not filepath or is_secret_path(filepath):
        return None
    chunk_id = str(raw.get("chunk_id") or raw.get("todo_id") or "")
    if not chunk_id:
        return None
    score = float(raw.get("score") or raw.get("rrf_score") or raw.get("bm25_score") or raw.get("vector_score") or 0.0)
    line_start = int(raw.get("line_start") or raw.get("line_number") or raw.get("line") or 1)
    line_end = int(raw.get("line_end") or line_start)
    content_hash = _content_hash(raw)
    citation = f"{filepath}:{line_start}-{line_end} [{chunk_id}]"
    content = redact_secret_mentions(str(raw.get("content") or raw.get("text") or ""))
    return ScoredChunk(
        chunk_id=chunk_id,
        document_id=str(raw.get("document_id") or filepath),
        filepath=filepath,
        line_start=line_start,
        line_end=line_end,
        content=content,
        score=score,
        bm25_score=float(raw.get("bm25_score") or (score if source == "bm25" else 0.0)),
        vector_score=float(raw.get("vector_score") or (score if source == "vector" else 0.0)),
        rerank_score=float(raw.get("rerank_score") or 0.0),
        rrf_score=float(raw.get("rrf_score") or 0.0),
        confidence=min(1.0, max(0.0, abs(score))),
        content_hash=content_hash,
        citations=[citation],
        lang=str(raw.get("lang") or ""),
        chunk_type=str(raw.get("chunk_type") or ""),
        symbol_name=str(raw.get("symbol_name") or ""),
    )


def parse_chunks(response: dict[str, Any], *, source: str = "hybrid") -> list[ScoredChunk]:
    chunks: list[ScoredChunk] = []
    for raw in response.get("results", []):
        parsed = parse_chunk(raw, source=source)
        if parsed is not None:
            chunks.append(parsed)
    return chunks


def chunk_by_id(chunk_id: str, *, db_path: str | None = None) -> ScoredChunk | None:
    path = Path(db_path or os.environ.get("RAGD_DB_PATH") or str(Path.home() / ".ragd" / "ragd.db")).expanduser()
    if not path.exists():
        return None
    uri = f"file:{path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT id AS chunk_id, filepath, content, lang, chunk_type, symbol_name, line_start, line_end, content_hash, summary, git_commit FROM chunks WHERE id=? AND status='active'",
            (chunk_id,),
        ).fetchone()
        if row is None:
            return None
        return parse_chunk(dict(row), source="explain")
    finally:
        conn.close()


def chunk_to_json(chunk: ScoredChunk) -> dict[str, Any]:
    return asdict(chunk)


def ping_latency(client: RagdClient) -> float:
    started = time.perf_counter()
    client.health()
    return (time.perf_counter() - started) * 1000
