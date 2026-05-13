"""Tests for dominion_loader.graph — knowledge graph CRUD and ingest."""
from __future__ import annotations

from pathlib import Path

import pytest

from dominion_loader.graph import KnowledgeGraph, KGNode, KGEdge


@pytest.fixture
def kg(tmp_path: Path) -> KnowledgeGraph:
    db = tmp_path / "kg.db"
    g = KnowledgeGraph(db)
    yield g
    g.close()


def _node(node_id: str, kind: str = "file", name: str = "src.py") -> KGNode:
    """Helper to build a KGNode with sensible defaults."""
    return KGNode(
        node_id=node_id,
        kind=kind,
        name=name,
        filepath=name,
        language="python",
        line_start=0,
        line_end=0,
    )


def _edge(from_id: str, to_id: str, relation: str = "imports") -> KGEdge:
    """Helper to build a KGEdge."""
    return KGEdge(from_id=from_id, to_id=to_id, relation=relation, filepath="src.py")


# ---------------------------------------------------------------------------
# Node CRUD
# ---------------------------------------------------------------------------
def test_add_and_get_node(kg: KnowledgeGraph) -> None:
    node = _node("n1", kind="file", name="dominion_loader/ignore.py")
    kg.add_node(node)
    retrieved = kg.get_node("n1")
    assert retrieved is not None
    assert retrieved.node_id == "n1"
    assert retrieved.kind == "file"
    assert retrieved.name == "dominion_loader/ignore.py"


def test_get_missing_node(kg: KnowledgeGraph) -> None:
    assert kg.get_node("nonexistent") is None


def test_add_node_idempotent(kg: KnowledgeGraph) -> None:
    """Upserting the same node twice doesn't create duplicates."""
    node = _node("n2", kind="chunk", name="chunk1")
    kg.add_node(node)
    kg.add_node(node)
    assert len(kg.list_nodes()) == 1


def test_list_nodes_filtered_by_kind(kg: KnowledgeGraph) -> None:
    kg.add_node(_node("f1", kind="file"))
    kg.add_node(_node("f2", kind="file"))
    kg.add_node(_node("c1", kind="chunk"))
    files = kg.list_nodes(kind="file")
    assert len(files) == 2
    assert all(n.kind == "file" for n in files)


# ---------------------------------------------------------------------------
# Edge CRUD
# ---------------------------------------------------------------------------
def test_add_edge(kg: KnowledgeGraph) -> None:
    kg.add_node(_node("n_src", name="src.py"))
    kg.add_node(_node("n_dst", name="dst.py"))
    kg.add_edge(_edge("n_src", "n_dst", "imports"))
    neighbors = kg.neighbors("n_src")
    assert "n_dst" in neighbors


def test_edge_idempotent(kg: KnowledgeGraph) -> None:
    """INSERT OR IGNORE means same edge twice stays one row."""
    kg.add_node(_node("a"))
    kg.add_node(_node("b"))
    kg.add_edge(_edge("a", "b"))
    kg.add_edge(_edge("a", "b"))
    assert kg.stats()["edges"] == 1


def test_neighbors_empty_for_isolated_node(kg: KnowledgeGraph) -> None:
    kg.add_node(_node("isolated"))
    assert kg.neighbors("isolated") == []


def test_neighbors_filtered_by_relation(kg: KnowledgeGraph) -> None:
    kg.add_node(_node("s"))
    kg.add_node(_node("t1"))
    kg.add_node(_node("t2"))
    kg.add_edge(_edge("s", "t1", "imports"))
    kg.add_edge(_edge("s", "t2", "defines"))
    imports = kg.neighbors("s", relation="imports")
    assert imports == ["t1"]


# ---------------------------------------------------------------------------
# stats()
# ---------------------------------------------------------------------------
def test_stats_correct(kg: KnowledgeGraph) -> None:
    kg.add_node(_node("a"))
    kg.add_node(_node("b"))
    kg.add_edge(_edge("a", "b"))
    stats = kg.stats()
    assert stats["nodes"] == 2
    assert stats["edges"] == 1


def test_stats_empty(kg: KnowledgeGraph) -> None:
    stats = kg.stats()
    assert stats["nodes"] == 0
    assert stats["edges"] == 0


# ---------------------------------------------------------------------------
# KGNode field round-trip
# ---------------------------------------------------------------------------
def test_node_fields_round_trip(kg: KnowledgeGraph) -> None:
    node = KGNode(
        node_id="n99",
        kind="symbol",
        name="my_function",
        filepath="src/main.py",
        language="python",
        line_start=10,
        line_end=20,
    )
    kg.add_node(node)
    retrieved = kg.get_node("n99")
    assert retrieved.kind == "symbol"
    assert retrieved.name == "my_function"
    assert retrieved.filepath == "src/main.py"
    assert retrieved.language == "python"
    assert retrieved.line_start == 10
    assert retrieved.line_end == 20
