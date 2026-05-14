from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .chunker import chunk_file
from .config import CHUNKER_HOST, CHUNKER_PORT


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/health":
            self._json({"ok": True, "service": "ragd_chunker"})
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        if self.path != "/chunk":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        chunks = [chunk.to_dict() for chunk in chunk_file(payload["filepath"], payload.get("content", ""), payload.get("lang"))]
        self._json({"chunks": chunks})

    def log_message(self, *_args) -> None:
        return

    def _json(self, payload: dict) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=CHUNKER_HOST)
    parser.add_argument("--port", type=int, default=CHUNKER_PORT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.check:
        print(json.dumps({"ok": True, "host": args.host, "port": args.port}))
        return 0
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
