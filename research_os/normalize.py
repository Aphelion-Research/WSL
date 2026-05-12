from __future__ import annotations

from dataclasses import dataclass

from .cleaner import clean_text, html_to_text_fallback, strip_noise


@dataclass(frozen=True)
class NormalizationResult:
    text: str
    method: str
    removed_noise: bool


def normalize_raw_text(raw: str, *, content_type: str | None) -> NormalizationResult:
    raw = raw or ""
    is_html = False
    if content_type and "html" in content_type.lower():
        is_html = True
    if "<html" in raw.lower() or "</html>" in raw.lower():
        is_html = True

    if is_html:
        stripped = strip_noise(raw)
        text = html_to_text_fallback(stripped)
        return NormalizationResult(text=text, method="html_to_text", removed_noise=(stripped != raw))

    return NormalizationResult(text=clean_text(raw), method="plain_clean", removed_noise=False)

