from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any, Iterable


def to_jsonable(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "_asdict"):
        return {k: to_jsonable(v) for k, v in value._asdict().items()}
    if hasattr(value, "dtype") and getattr(value.dtype, "names", None):
        rows = []
        for row in value:
            item = {}
            for name in value.dtype.names:
                cell = row[name]
                if hasattr(cell, "item"):
                    cell = cell.item()
                item[name] = to_jsonable(cell)
            rows.append(item)
        return rows
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def rows_from(value: Any) -> list[Any]:
    data = to_jsonable(value)
    if data is None:
        return []
    if isinstance(data, list):
        return data
    return [data]


def stable_json(value: Any, *, pretty: bool = True) -> str:
    kwargs = {"sort_keys": True, "default": str}
    if pretty:
        kwargs["indent"] = 2
    return json.dumps(to_jsonable(value), **kwargs)


def _write_text(text: str, out: str | None) -> None:
    if out:
        path = Path(out).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    else:
        print(text)


def emit(value: Any, fmt: str = "json", out: str | None = None) -> None:
    data = to_jsonable(value)
    if fmt == "json":
        _write_text(stable_json(data), out)
        return
    if fmt == "jsonl":
        text = "\n".join(json.dumps(row, sort_keys=True, default=str) for row in rows_from(data))
        _write_text(text, out)
        return
    if fmt == "csv":
        rows = rows_from(data)
        if not rows:
            _write_text("", out)
            return
        if not all(isinstance(row, dict) for row in rows):
            rows = [{"value": row} for row in rows]
        fieldnames = sorted({key for row in rows for key in row.keys()})
        if out:
            path = Path(out).expanduser()
            path.parent.mkdir(parents=True, exist_ok=True)
            handle = path.open("w", newline="", encoding="utf-8")
            close = True
        else:
            handle = sys.stdout
            close = False
        try:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        finally:
            if close:
                handle.close()
        return
    raise SystemExit(f"Unsupported output format: {fmt}")
