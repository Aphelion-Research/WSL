from __future__ import annotations


def summarize(text: str) -> dict[str, object]:
    try:
        from local_llm.ollama import summarize as local_summarize
    except Exception as exc:
        return {"ok": False, "disabled": True, "error": f"local_llm unavailable: {exc}"}
    return local_summarize(text)
