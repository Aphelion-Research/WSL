from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from typing import Any

from .ragd_client import RagdClient


@dataclass(frozen=True)
class LedgerEntry:
    id: str
    kind: str
    session_id: str
    filepath: str
    text: str
    created_at: str
    tags: list[str]


def _parse_since(value: str | None) -> datetime | None:
    if not value:
        return None
    now = datetime.now(timezone.utc)
    if value.endswith("d"):
        return now - timedelta(days=int(value[:-1]))
    if value.endswith("h"):
        return now - timedelta(hours=int(value[:-1]))
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _after(created_at: str, since: datetime | None) -> bool:
    if since is None:
        return True
    try:
        return datetime.fromisoformat(created_at.replace("Z", "+00:00")) >= since
    except ValueError:
        return True


def list_entries(*, kind: str | None = None, session: str | None = None, tag: str | None = None, since: str | None = None, limit: int = 50, client: RagdClient | None = None) -> list[LedgerEntry]:
    client = client or RagdClient()
    cutoff = _parse_since(since)
    entries: list[LedgerEntry] = []
    if kind in (None, "decision"):
        for row in client.decisions(limit=limit).get("decisions", []):
            tags = row.get("tags") or []
            if isinstance(tags, str):
                tags = []
            entry = LedgerEntry(
                id=str(row.get("id")),
                kind="decision",
                session_id=str(row.get("session_id") or ""),
                filepath=str(row.get("filepath") or ""),
                text=str(row.get("decision") or row.get("text") or ""),
                created_at=str(row.get("created_at") or ""),
                tags=list(tags),
            )
            if session and entry.session_id != session:
                continue
            if tag and tag not in entry.tags:
                continue
            if not _after(entry.created_at, cutoff):
                continue
            entries.append(entry)
    return entries[:limit]


def show_entry(entry_id: str, *, client: RagdClient | None = None) -> LedgerEntry | None:
    for entry in list_entries(limit=200, client=client):
        if entry.id == str(entry_id):
            return entry
    return None


def search_entries(query: str, *, limit: int = 20, client: RagdClient | None = None) -> list[LedgerEntry]:
    lower = query.lower()
    return [entry for entry in list_entries(limit=200, client=client) if lower in f"{entry.text} {entry.filepath} {' '.join(entry.tags)}".lower()][:limit]


def entries_to_dict(entries: list[LedgerEntry]) -> list[dict[str, Any]]:
    return [asdict(entry) for entry in entries]
