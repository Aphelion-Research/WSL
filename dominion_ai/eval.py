from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .planner import plan
from .rerank import rerank
from .retrieval import retrieve


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _dcg(relevances: list[int]) -> float:
    import math

    return sum((2**rel - 1) / math.log2(index + 2) for index, rel in enumerate(relevances))


def run_eval(bundle: str | Path, *, top_k: int = 10, write_report: bool = True) -> dict[str, Any]:
    bundle = Path(bundle)
    queries = _read_jsonl(bundle / "queries.jsonl")
    expected_rows = {row["query"]: row for row in _read_jsonl(bundle / "expected_chunks.jsonl")}
    total = max(1, len(queries))
    recall_sum = 0.0
    mrr_sum = 0.0
    ndcg_sum = 0.0
    citation_sum = 0.0
    details: list[dict[str, Any]] = []
    started = time.time()
    for row in queries:
        query = row["query"]
        expected = [str(item) for item in expected_rows.get(query, {}).get("expected_chunk_ids", [])]
        retrieval_plan = plan(query, {"top_k": top_k, "intent": row.get("intent")})
        chunks = rerank(retrieval_plan, retrieve(retrieval_plan))[:top_k]
        observed = [chunk.chunk_id for chunk in chunks]
        hits = [chunk_id for chunk_id in observed if chunk_id in expected]
        recall = len(set(hits)) / max(1, len(set(expected)))
        rr = 0.0
        for index, chunk_id in enumerate(observed, start=1):
            if chunk_id in expected:
                rr = 1.0 / index
                break
        relevances = [1 if chunk_id in expected else 0 for chunk_id in observed]
        ideal = sorted(relevances, reverse=True)
        ndcg = _dcg(relevances) / (_dcg(ideal) or 1.0)
        citation_accuracy = 1.0 if all(chunk.citations for chunk in chunks) and chunks else 0.0
        recall_sum += recall
        mrr_sum += rr
        ndcg_sum += ndcg
        citation_sum += citation_accuracy
        details.append({"query": query, "expected": expected, "observed": observed, "recall": recall, "mrr": rr, "ndcg": ndcg})
    result = {
        "ok": True,
        "bundle": str(bundle),
        "top_k": top_k,
        "queries": len(queries),
        "elapsed_ms": round((time.time() - started) * 1000, 3),
        "metrics": {
            f"recall@{top_k}": recall_sum / total,
            "mrr": mrr_sum / total,
            f"ndcg@{top_k}": ndcg_sum / total,
            "citation_accuracy": citation_sum / total,
        },
        "details": details,
    }
    if write_report:
        out_dir = Path("reports/eval")
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"{bundle.name}-{time.strftime('%Y%m%d-%H%M%S', time.gmtime())}.json"
        out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
        result["report"] = str(out)
    return result
