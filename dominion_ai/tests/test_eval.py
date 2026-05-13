from __future__ import annotations

import json

from dominion_ai.eval import _dcg, _read_jsonl


def test_eval_bundle_roundtrip(tmp_path):
    path = tmp_path / "queries.jsonl"
    path.write_text(json.dumps({"query": "x"}) + "\n", encoding="utf-8")
    assert _read_jsonl(path)[0]["query"] == "x"
    assert _dcg([1, 0]) > 0
