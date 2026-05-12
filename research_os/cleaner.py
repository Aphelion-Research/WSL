from __future__ import annotations

import re


NOISE_RE = re.compile(r"<(script|style|noscript|svg|nav|header|footer|aside)\b.*?</\1>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"[ \t]+")
BLANK_RE = re.compile(r"\n{3,}")


def strip_noise(html: str) -> str:
    return NOISE_RE.sub(" ", html)


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = SPACE_RE.sub(" ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = BLANK_RE.sub("\n\n", text)
    return text.strip()


def html_to_text_fallback(html: str) -> str:
    html = strip_noise(html)
    html = re.sub(r"</(h[1-6])>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"<h([1-6])[^>]*>", lambda match: "\n" + ("#" * int(match.group(1))) + " ", html, flags=re.IGNORECASE)
    html = re.sub(r"</(p|div|section|article|li|br)>", "\n", html, flags=re.IGNORECASE)
    text = TAG_RE.sub(" ", html)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    return clean_text(text)
