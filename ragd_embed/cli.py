from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from .cache import EmbeddingCache
from .config import load_config
from .pipeline import run_embedding_pipeline


def _json(data: dict) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def cmd_run(args: argparse.Namespace) -> int:
    try:
        cfg = load_config(require_key=True)
        stats = run_embedding_pipeline(cfg=cfg, changed_only=args.changed_only, show_progress=not args.json)
        from ragd_hnsw.config import default_index_path
        from ragd_hnsw.index import HNSWIndex
        from ragd_hnsw.sync import sync_index

        index = HNSWIndex(cfg.dim, default_index_path(cfg.provider, cfg.model, cfg.dim))
        sync_stats = sync_index(cfg.ragd_db_path, cfg.cache_path, index)
        payload = {"ok": True, "stats": asdict(stats), "hnsw_sync": asdict(sync_stats), "provider": cfg.provider, "model": cfg.model}
    except Exception as exc:
        payload = {"ok": False, "error": str(exc)}
        if args.json:
            _json(payload)
        else:
            print(payload["error"])
        return 2
    if args.json:
        _json(payload)
    else:
        print(f"embedded vectors stored: {stats.vectors_stored}; cache_hits={stats.cache_hits}; api_batches={stats.api_batches}")
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    cfg = load_config(require_key=False)
    cache = EmbeddingCache(cfg.cache_path)
    payload = {"ok": True, "provider": cfg.provider, "model": cfg.model, "dim": cfg.dim, "cache": cache.stats(), "api_key_present": bool(cfg.api_key)}
    if args.json:
        _json(payload)
    else:
        print(f"provider={cfg.provider} model={cfg.model} dim={cfg.dim} cache_entries={payload['cache']['entries']} api_key_present={payload['api_key_present']}")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    cfg = load_config(require_key=False)

    # API key only required for external providers (not ollama)
    api_key_required = cfg.provider != "ollama"
    api_key_ok = bool(cfg.api_key) if api_key_required else True

    payload = {
        "ok": api_key_ok,
        "provider": cfg.provider,
        "model": cfg.model,
        "dim": cfg.dim,
        "api_key_env": cfg.api_key_env,
        "api_key_present": bool(cfg.api_key),
        "api_key_required": api_key_required,
        "local_provider": cfg.provider == "ollama",
        "cache": EmbeddingCache(cfg.cache_path).stats(),
    }

    if api_key_required and not cfg.api_key:
        payload["error"] = f"{cfg.api_key_env} is not set; dominion embed run will fail closed"

    if args.json:
        _json(payload)
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["ok"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dominion embed")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("run")
    p.add_argument("--changed-only", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_run)
    p = sub.add_parser("stats")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_stats)
    p = sub.add_parser("doctor")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_doctor)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
