from __future__ import annotations

from local_llm.prompts import claims_prompt, query_expand_prompt, summarize_prompt, tag_prompt


def test_prompts_include_text():
    assert "gold" in summarize_prompt("gold")
    assert "JSON array" in tag_prompt("gold")
    assert "claim" in claims_prompt("gold").lower()
    assert "search phrases" in query_expand_prompt("gold")
