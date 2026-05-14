from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .query import semantic_query


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/health":
            self._json({"ok": True, "service": "ragd_hnsw"})
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        if self.path != "/query/semantic":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        try:
            payload = semantic_query(body.get("q") or body.get("query") or "", top_k=int(body.get("top_k", body.get("limit", 20))))
            self._json(payload)
        except Exception as exc:
            self._json({"ok": False, "error": str(exc)}, status=503)

    def log_message(self, *_args) -> None:
        return

    def _json(self, payload: dict, *, status: int = 200) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main() -> int:
    host = os.environ.get("RAGD_SEMANTIC_HOST", "127.0.0.1")
    port = int(os.environ.get("RAGD_SEMANTIC_PORT", "7476"))
    ThreadingHTTPServer((host, port), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
