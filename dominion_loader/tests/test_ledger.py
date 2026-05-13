"""Tests for dominion_loader.ledger — append, idempotency, schema."""
from __future__ import annotations

import pytest
from pathlib import Path

from dominion_loader.ledger import Ledger, VALID_KINDS


@pytest.fixture
def ledger(tmp_path: Path) -> Ledger:
    db = tmp_path / "ledger.db"
    l = Ledger(db)
    yield l
    l.close()


def test_append_returns_id(ledger: Ledger) -> None:
    eid = ledger.append("decision", {"text": "Use SQLite for manifest"})
    assert isinstance(eid, int) and eid > 0


def test_append_idempotent_on_same_content(ledger: Ledger) -> None:
    """Same (session_id, kind, payload) → same entry id, no duplicate."""
    payload = {"text": "Use WAL mode"}
    id1 = ledger.append("decision", payload, session_id="sess1")
    id2 = ledger.append("decision", payload, session_id="sess1")
    assert id1 == id2


def test_append_different_payload_different_entry(ledger: Ledger) -> None:
    id1 = ledger.append("assumption", {"text": "RAGD runs at :7474"})
    id2 = ledger.append("assumption", {"text": "RAGD runs at :9999"})
    assert id1 != id2


def test_invalid_kind_raises(ledger: Ledger) -> None:
    with pytest.raises(ValueError, match="Unknown ledger kind"):
        ledger.append("bogus_kind", {})


def test_all_valid_kinds_accepted(ledger: Ledger) -> None:
    for kind in VALID_KINDS:
        eid = ledger.append(kind, {"test": True}, session_id=f"sess-{kind}")
        assert eid > 0


def test_tags_stored(ledger: Ledger) -> None:
    eid = ledger.append("risk", {"text": "Cache may grow large"}, tags=["cache", "storage"])
    entries = ledger.query_kind("risk")
    assert any(e.entry_id == eid and "cache" in e.tags for e in entries)


def test_query_kind_returns_entries(ledger: Ledger) -> None:
    ledger.append("interface", {"text": "LoadedFile v1"})
    ledger.append("interface", {"text": "ManifestEntry v1"})
    ledger.append("decision", {"text": "Use sha256"})

    interfaces = ledger.query_kind("interface")
    assert len(interfaces) == 2
    decisions = ledger.query_kind("decision")
    assert len(decisions) == 1


def test_stats(ledger: Ledger) -> None:
    ledger.append("decision", {"d": 1})
    ledger.append("decision", {"d": 2})
    ledger.append("risk", {"r": 1})
    stats = ledger.stats()
    assert stats["total"] == 3
    assert stats["decision"] == 2
    assert stats["risk"] == 1
