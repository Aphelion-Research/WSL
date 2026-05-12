from __future__ import annotations

import re
from html import unescape

from .cleaner import clean_text, html_to_text_fallback
from .normalize import normalize_raw_text
from .models import ExtractedDocument


TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def _title_from_html(html: str) -> str:
    match = TITLE_RE.search(html)
    if not match:
        return "Untitled"
    title = re.sub(r"\s+", " ", unescape(match.group(1))).strip()
    return title or "Untitled"


def _extract_with_bs4(html: str) -> tuple[str, str] | None:
    try:
        from bs4 import BeautifulSoup
    except Exception:
        return None
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "nav", "header", "footer", "aside"]):
        tag.decompose()
    title = soup.title.get_text(" ", strip=True) if soup.title else "Untitled"
    for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        level = int(heading.name[1])
        heading.insert_before(soup.new_string("\n" + ("#" * level) + " "))
        heading.append(soup.new_string("\n"))
    text = soup.get_text("\n")
    return title or "Untitled", clean_text(text)


def extract(
    raw: str,
    *,
    url: str,
    final_url: str | None,
    source_name: str,
    fetched_at_utc: str,
    content_hash: str | None,
    trust: str,
    adapter_name: str,
    content_type: str | None,
) -> ExtractedDocument:
    extracted = _extract_with_bs4(raw)
    if extracted:
        title, body = extracted
    else:
        title = _title_from_html(raw)
        norm = normalize_raw_text(raw, content_type=content_type)
        body = norm.text
    frontmatter = (
        "---\n"
        f"source_name: {source_name}\n"
        f"url: {url}\n"
        f"final_url: {final_url or ''}\n"
        f"adapter: {adapter_name}\n"
        f"content_type: {content_type or ''}\n"
        f"fetched_at_utc: {fetched_at_utc}\n"
        f"content_hash: {content_hash or ''}\n"
        f"trust: {trust}\n"
        "---\n\n"
    )
    markdown = frontmatter + f"# {title}\n\n{body}\n"
    normalization = normalize_raw_text(raw, content_type=content_type)
    return ExtractedDocument(
        title=title,
        markdown=markdown,
        text_length=len(body),
        normalization={"method": normalization.method, "removed_noise": normalization.removed_noise},
    )
