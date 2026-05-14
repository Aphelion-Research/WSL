from __future__ import annotations

import numpy as np

from ragd_hnsw.index import HNSWIndex


def test_build_query_save_load(tmp_path):
    path = tmp_path / "index.bin"
    vectors = np.asarray([[1.0, 0.0], [0.0, 1.0], [0.9, 0.1]], dtype=np.float32)
    ids = np.asarray([10, 11, 12], dtype=np.int64)
    index = HNSWIndex(2, path)
    index.build(vectors, ids)
    before = index.query(np.asarray([1.0, 0.0], dtype=np.float32), top_k=2)
    assert before[0][0] in {10, 12}
    loaded = HNSWIndex(2, path)
    loaded.load()
    after = loaded.query(np.asarray([1.0, 0.0], dtype=np.float32), top_k=2)
    assert [item[0] for item in after] == [item[0] for item in before]


def test_atomic_write_preserves_old_index(tmp_path, monkeypatch):
    path = tmp_path / "index.bin"
    index = HNSWIndex(2, path)
    index.build(np.asarray([[1.0, 0.0]], dtype=np.float32), np.asarray([1], dtype=np.int64))
    old_size = path.stat().st_size

    def fail_replace(src, dst):
        raise RuntimeError("simulated crash")

    monkeypatch.setattr("ragd_hnsw.index.os.replace", fail_replace)
    try:
        index.add(np.asarray([[0.0, 1.0]], dtype=np.float32), np.asarray([2], dtype=np.int64))
        index.save()
    except RuntimeError:
        pass
    assert path.exists()
    assert path.stat().st_size == old_size
