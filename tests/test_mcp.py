"""Smoke test for the stdio MCP server."""

import json
import os
import queue
import subprocess
import sys

import pytest

pytest.importorskip("mcp") if not os.environ.get("OCALC_REQUIRE_MCP") else None


def _require_mcp():
    if os.environ.get("OCALC_REQUIRE_MCP"):
        import mcp  # noqa: F401
        return
    pytest.importorskip("mcp")


def _request(proc, message: dict, timeout: float = 20) -> dict:
    assert proc.stdin is not None and proc.stdout is not None
    proc.stdin.write(json.dumps(message) + "\n")
    proc.stdin.flush()
    found: queue.Queue[str] = queue.Queue()

    def read() -> None:
        found.put(proc.stdout.readline())

    reader = __import__("threading").Thread(target=read, daemon=True)
    reader.start()
    reader.join(timeout)
    if reader.is_alive():
        proc.kill()
        raise AssertionError("MCP server did not answer")
    line = found.get()
    if not line:
        proc.kill()
        err = proc.stderr.read() if proc.stderr else ""
        raise AssertionError(err or "empty response")
    return json.loads(line)


def test_mcp_stdio_lists_the_tools():
    _require_mcp()
    proc = subprocess.Popen(
        [sys.executable, "-c", "from ocalc.mcp_server import serve; serve()"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    try:
        started = _request(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "ocalc-test", "version": "0.1.0"},
                },
            },
        )
        assert started["id"] == 1
        assert "result" in started, started
        assert proc.stdin is not None
        proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        proc.stdin.flush()
        listed = _request(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        names = {tool["name"] for tool in listed["result"]["tools"]}
        assert names == {"measure_function", "annotate_function"}
    finally:
        proc.kill()
        proc.wait(timeout=5)
