from __future__ import annotations

import os


CHUNKER_HOST = os.environ.get("RAGD_CHUNKER_HOST", "127.0.0.1")
CHUNKER_PORT = int(os.environ.get("RAGD_CHUNKER_PORT", "7475"))
