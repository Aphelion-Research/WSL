from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .models import Source


ROOT = Path(os.environ.get("DOMINION_ROOT", Path.home() / "Dominion")).resolve()
RESEARCH_DIR = ROOT / "research"
SOURCES_YAML = RESEARCH_DIR / "sources.yaml"
DB_PATH = RESEARCH_DIR / "research.db"
USER_AGENT = "DominionResearchOS/0.1"


@dataclass(frozen=True)
class ResearchPaths:
    root: Path = ROOT
    research: Path = RESEARCH_DIR
    db: Path = DB_PATH
    sources_yaml: Path = SOURCES_YAML
    raw: Path = RESEARCH_DIR / "raw"
    markdown: Path = RESEARCH_DIR / "markdown"
    extracted: Path = RESEARCH_DIR / "extracted"
    reports: Path = RESEARCH_DIR / "reports"
    logs: Path = RESEARCH_DIR / "logs"
    cache: Path = RESEARCH_DIR / "cache"


DEFAULT_SOURCES: list[dict[str, Any]] = [
    {"name": "crawl4ai_docs", "base_url": "https://docs.crawl4ai.com/", "trust": "high", "rate_limit_sec": 2, "enabled": True, "adapter_preference": "requests"},
    {"name": "ollama_docs", "base_url": "https://github.com/ollama/ollama/tree/main/docs", "trust": "high", "rate_limit_sec": 2, "enabled": True, "adapter_preference": "requests"},
    {"name": "playwright_docs", "base_url": "https://playwright.dev/python/", "trust": "high", "rate_limit_sec": 2, "enabled": True, "adapter_preference": "requests"},
    {"name": "vllm_docs", "base_url": "https://docs.vllm.ai/", "trust": "high", "rate_limit_sec": 2, "enabled": True, "adapter_preference": "requests"},
    {"name": "mql5_docs", "base_url": "https://www.mql5.com/en/docs", "trust": "high", "rate_limit_sec": 2, "enabled": True, "adapter_preference": "requests"},
]


def paths() -> ResearchPaths:
    return ResearchPaths()


def ensure_dirs(p: ResearchPaths | None = None) -> None:
    p = p or paths()
    for directory in (p.research, p.raw, p.markdown, p.extracted, p.reports, p.logs, p.cache):
        directory.mkdir(parents=True, exist_ok=True)


def write_default_sources(path: Path = SOURCES_YAML) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(yaml.safe_dump({"sources": DEFAULT_SOURCES}, sort_keys=False), encoding="utf-8")


def load_sources(path: Path = SOURCES_YAML) -> list[Source]:
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    sources: list[Source] = []
    for item in data.get("sources", []):
        sources.append(
            Source(
                name=str(item["name"]),
                base_url=str(item["base_url"]),
                trust=str(item.get("trust", "unknown")),
                rate_limit_sec=float(item.get("rate_limit_sec", 2.0)),
                enabled=bool(item.get("enabled", True)),
                adapter_preference=str(item.get("adapter_preference", "requests") or "requests"),
            )
        )
    return sources


def upsert_source_yaml(source: Source, path: Path = SOURCES_YAML) -> None:
    write_default_sources(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {"sources": []}
    items = [item for item in data.get("sources", []) if item.get("name") != source.name]
    items.append(
        {
            "name": source.name,
            "base_url": source.base_url,
            "trust": source.trust,
            "rate_limit_sec": source.rate_limit_sec,
            "enabled": source.enabled,
            "adapter_preference": source.adapter_preference,
        }
    )
    path.write_text(yaml.safe_dump({"sources": items}, sort_keys=False), encoding="utf-8")
