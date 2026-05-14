from __future__ import annotations

import sqlite3

from ragd_graph.graph import build_graph, callees, stats


def test_build_graph_from_chunks(tmp_path):
    db = tmp_path / "ragd.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE chunks(id INTEGER PRIMARY KEY, filepath TEXT, symbol_name TEXT, chunk_type TEXT, qualified_name TEXT, docstring TEXT, imports_json TEXT, calls_json TEXT, is_public INTEGER, status TEXT)")
    conn.execute("INSERT INTO chunks VALUES (1, '/repo/a.py', 'f', 'function', 'pkg.a.f', 'doc', '[\"os\"]', '[\"g\"]', 1, 'active')")
    conn.commit()
    conn.close()
    result = build_graph(db)
    assert result.nodes >= 3
    assert result.by_relation["calls"] == 1
    assert callees("pkg.a.f", db)[0]["to_node"] == "symbol:g"
    assert stats(db).edges >= 2
