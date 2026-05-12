#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from typing import Dict, Any

import requests
from mcp.server.fastmcp import FastMCP

RAGD_URL = os.environ.get("RAGD_URL", "http://127.0.0.1:7474/mcp")

mcp = FastMCP("ragd")


def _ragd_tool(name: str, arguments: Dict[str, Any]) -> str:
    """
    Call RAGD's HTTP MCP-ish endpoint and return JSON text.
    Important: return plain string to avoid MCP schema/serialization issues.
    """
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": arguments,
            },
        }
        r = requests.post(RAGD_URL, json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        return json.dumps(data, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps(
            {
                "error": str(e),
                "tool": name,
                "ragd_url": RAGD_URL,
            },
            indent=2,
        )


@mcp.tool()
def ragd_query(q: str, mode: str = "hybrid", top_k: int = 8) -> str:
    """Search the RAGD hybrid knowledge base."""
    return _ragd_tool("ragd_query", {"q": q, "mode": mode, "top_k": top_k})


@mcp.tool()
def ragd_handoff_read() -> str:
    """Read the full Dominion/RAGD project handoff context."""
    return _ragd_tool("ragd_handoff_read", {})


@mcp.tool()
def ragd_todo_list(limit: int = 20) -> str:
    """List open RAGD TODOs."""
    return _ragd_tool("ragd_todo_list", {"limit": limit})


@mcp.tool()
def ragd_remember(kind: str, content: str, filepath: str = "") -> str:
    """Store a RAGD note, decision, or warning."""
    return _ragd_tool(
        "ragd_remember",
        {
            "kind": kind,
            "content": content,
            "filepath": filepath,
            "tags": [],
        },
    )


@mcp.tool()
def ragd_todo_add(content: str, filepath: str = "", priority: int = 5) -> str:
    """Add a TODO to RAGD."""
    return _ragd_tool(
        "ragd_todo_add",
        {
            "content": content,
            "filepath": filepath,
            "priority": priority,
            "kind": "TODO",
            "line": 0,
        },
    )


@mcp.tool()
def ragd_deadzone_report(path: str = "/home/Martin/Dominion") -> str:
    """Get stale/dead-zone findings from RAGD."""
    return _ragd_tool("ragd_deadzone_report", {"path": path})


if __name__ == "__main__":
    try:
        # Default is stdio. Keep stdout reserved for MCP protocol only.
        mcp.run()
    except Exception as e:
        print(f"ragd_mcp_stdio fatal: {e}", file=sys.stderr)
        raise
