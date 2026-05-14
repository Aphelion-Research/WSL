from __future__ import annotations


def summarize(text: str) -> dict[str, object]:
    return {
        "ok": False,
        "disabled": True,
        "error": "Local generation was removed; frontier agents handle summarization and RAGD provides retrieval context.",
    }
