from __future__ import annotations

from dominion_ai.ledger import list_entries, search_entries


class FakeClient:
    def decisions(self, *, limit):
        return {"decisions": [{"id": 1, "session_id": "s", "filepath": "f", "decision": "Use RAGD spine", "created_at": "2026-05-13T00:00:00Z", "tags": ["decision"]}]}


def test_ledger_filters_kind_and_search():
    entries = list_entries(kind="decision", client=FakeClient())
    assert entries[0].text == "Use RAGD spine"
    assert search_entries("spine", client=FakeClient())[0].id == "1"
