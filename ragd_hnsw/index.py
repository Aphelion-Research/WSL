from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import numpy as np

try:
    import hnswlib  # type: ignore
except Exception:  # pragma: no cover - exercised in environments without hnswlib
    hnswlib = None


class HNSWIndex:
    def __init__(self, dim: int, path: Path, space: str = "cosine"):
        self.dim = int(dim)
        self.path = Path(path).expanduser()
        self.space = space
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ids = np.asarray([], dtype=np.int64)
        self._vectors = np.empty((0, self.dim), dtype=np.float32)
        self._deleted: set[int] = set()
        self._index = hnswlib.Index(space=space, dim=self.dim) if hnswlib is not None else None
        self.backend = "hnswlib" if hnswlib is not None else "exact_numpy_fallback"

    @property
    def _meta_path(self) -> Path:
        return self.path.with_suffix(self.path.suffix + ".meta.json")

    def build(self, vectors: np.ndarray, ids: np.ndarray, ef_construction: int = 200, M: int = 16) -> None:
        vectors = np.asarray(vectors, dtype=np.float32)
        ids = np.asarray(ids, dtype=np.int64)
        if vectors.ndim != 2 or vectors.shape[1] != self.dim:
            raise ValueError(f"vectors must have shape (n, {self.dim})")
        self._vectors = vectors.copy()
        self._ids = ids.copy()
        self._deleted = set()
        if self._index is not None:
            self._index = hnswlib.Index(space=self.space, dim=self.dim)
            self._index.init_index(max_elements=max(1, len(ids)), ef_construction=ef_construction, M=M)
            if len(ids):
                self._index.add_items(vectors, ids)
            self._index.set_ef(100)
        self.save()

    def add(self, vectors: np.ndarray, ids: np.ndarray) -> None:
        vectors = np.asarray(vectors, dtype=np.float32)
        ids = np.asarray(ids, dtype=np.int64)
        if len(ids) == 0:
            return
        if len(self._ids) == 0:
            self.build(vectors, ids)
            return
        keep = [index for index, chunk_id in enumerate(ids) if int(chunk_id) not in set(map(int, self._ids))]
        if not keep:
            return
        new_vectors = vectors[keep]
        new_ids = ids[keep]
        self._vectors = np.vstack([self._vectors, new_vectors])
        self._ids = np.concatenate([self._ids, new_ids])
        if self._index is not None:
            try:
                self._index.add_items(new_vectors, new_ids)
            except RuntimeError:
                self.build(self._vectors, self._ids)

    def mark_deleted(self, chunk_id: int) -> None:
        chunk_id = int(chunk_id)
        self._deleted.add(chunk_id)
        if self._index is not None:
            try:
                self._index.mark_deleted(chunk_id)
            except RuntimeError:
                pass

    def query(self, vector: np.ndarray, top_k: int = 50) -> list[tuple[int, float]]:
        vector = np.asarray(vector, dtype=np.float32).reshape(1, self.dim)
        top_k = max(1, int(top_k))
        if self._index is not None and self.path.exists():
            labels, distances = self._index.knn_query(vector, k=min(top_k, max(1, len(self._ids))))
            pairs = [(int(label), float(distance)) for label, distance in zip(labels[0], distances[0]) if int(label) not in self._deleted]
            return pairs[:top_k]
        active = [(chunk_id, vec) for chunk_id, vec in zip(self._ids, self._vectors) if int(chunk_id) not in self._deleted]
        if not active:
            return []
        ids = np.asarray([item[0] for item in active], dtype=np.int64)
        vectors = np.asarray([item[1] for item in active], dtype=np.float32)
        q = vector[0]
        denom = (np.linalg.norm(vectors, axis=1) * max(float(np.linalg.norm(q)), 1e-12))
        distances = 1.0 - (vectors @ q) / np.maximum(denom, 1e-12)
        order = np.argsort(distances)[:top_k]
        return [(int(ids[index]), float(distances[index])) for index in order]

    def save(self) -> None:
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        if self._index is not None:
            self._index.save_index(str(tmp))
            os.replace(tmp, self.path)
        else:
            with tmp.open("wb") as handle:
                np.savez(handle, vectors=self._vectors, ids=self._ids, deleted=np.asarray(sorted(self._deleted), dtype=np.int64))
            os.replace(tmp, self.path)
        meta = {"dim": self.dim, "space": self.space, "backend": self.backend, "ids": [int(v) for v in self._ids], "deleted": sorted(self._deleted)}
        tmp_meta = self._meta_path.with_suffix(self._meta_path.suffix + ".tmp")
        tmp_meta.write_text(json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(tmp_meta, self._meta_path)

    def load(self) -> None:
        if not self.path.exists():
            raise FileNotFoundError(str(self.path))
        meta: dict[str, Any] = json.loads(self._meta_path.read_text(encoding="utf-8")) if self._meta_path.exists() else {}
        self._deleted = {int(v) for v in meta.get("deleted", [])}
        if self._index is not None and meta.get("backend") == "hnswlib":
            self._index.load_index(str(self.path))
            self._index.set_ef(100)
            self._ids = np.asarray(meta.get("ids", []), dtype=np.int64)
            self._vectors = np.empty((len(self._ids), self.dim), dtype=np.float32)
        else:
            data = np.load(self.path)
            self._vectors = np.asarray(data["vectors"], dtype=np.float32)
            self._ids = np.asarray(data["ids"], dtype=np.int64)
            if "deleted" in data:
                self._deleted |= {int(v) for v in data["deleted"]}

    def stats(self) -> dict[str, Any]:
        active = [int(v) for v in self._ids if int(v) not in self._deleted]
        return {
            "path": str(self.path),
            "exists": self.path.exists(),
            "backend": self.backend,
            "dim": self.dim,
            "space": self.space,
            "element_count": len(active),
            "deleted_count": len(self._deleted),
            "file_size_mb": round(self.path.stat().st_size / 1024 / 1024, 4) if self.path.exists() else 0.0,
        }
