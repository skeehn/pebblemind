"""Tiny MCP echo server used by robust tests (stdio JSON-RPC, no deps)."""
import json
import sys


def handle(msg):
    method = msg.get("method", "")
    mid = msg.get("id")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": mid, "result": {
            "protocolVersion": "2025-06-18",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "echo", "version": "0.0.1"},
        }}
    if mid is None:
        return None
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": mid, "result": {"tools": [{
            "name": "echo",
            "description": "Echo back the input text",
            "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
        }]}}
    if method == "tools/call":
        args = (msg.get("params") or {}).get("arguments") or {}
        return {"jsonrpc": "2.0", "id": mid, "result": {
            "content": [{"type": "text", "text": f"echo:{args.get('text', '')}"}],
            "isError": False,
        }}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": mid, "result": {}}
    return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "not found"}}


for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        msg = json.loads(line)
    except json.JSONDecodeError:
        continue
    resp = handle(msg)
    if resp:
        sys.stdout.write(json.dumps(resp, separators=(",", ":")) + "\n")
        sys.stdout.flush()
