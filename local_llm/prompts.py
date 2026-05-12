from __future__ import annotations


def summarize_prompt(text: str) -> str:
    return "Summarize the following evidence concisely with provenance-aware caveats:\n\n" + text


def tag_prompt(text: str) -> str:
    return "Return 5-10 lowercase tags for this text as a JSON array:\n\n" + text


def claims_prompt(text: str) -> str:
    return "Extract factual claims from this text. Return one claim per line and do not add unsupported claims:\n\n" + text


def query_expand_prompt(text: str) -> str:
    return "Expand this research query into precise related search phrases:\n\n" + text
