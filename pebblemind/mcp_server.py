"""Model Context Protocol (MCP) server for PebbleMind.

Exposes PebbleMind's capabilities (local chat, document Q&A, status) as MCP
tools/resources so any MCP client — Claude Desktop, editors, agent frameworks —
can use a fully local model. Speaks the standard JSON-RPC 2.0 protocol over
stdio (newline-delimited), so it plugs into any MCP host with zero extra
Python dependencies.

Run:  pebblemind mcp serve        (or)  python -m pebblemind.mcp_server
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Spec revisions in the wild; we speak 2025-06-18 but accept whatever the
# client requests (per spec, servers respond with a version they support).
MCP_PROTOCOL_VERSION = "2025-06-18"

MCP_SERVER_INFO = {"name": "pebblemind", "version": "0.1.0"}


def _tool_chat() -> Dict[str, Any]:
    return {
        "name": "chat",
        "description": (
            "Ask PebbleMind, a fully local AI assistant (no cloud). Send a "
            "message and receive a concise answer generated on-device. "
            "Streaming: attach _meta.progressToken to receive token-by-token "
            "notifications/progress while the answer generates."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "The user's message"},
                "use_rag": {
                    "type": "boolean",
                    "description": "Ground the answer in added documents (default true)",
                    "default": True,
                },
            },
            "required": ["message"],
        },
    }


def _tool_ask_documents() -> Dict[str, Any]:
    return {
        "name": "ask_documents",
        "description": (
            "Search the local document store (RAG) and answer strictly from "
            "the matching passages. Documents must have been added first."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "k": {"type": "integer", "description": "Number of passages (default 3)"},
            },
            "required": ["question"],
        },
    }


def _tool_add_documents() -> Dict[str, Any]:
    return {
        "name": "add_documents",
        "description": "Add text documents to the local vector store for later Q&A.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "documents": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string"},
                            "metadata": {"type": "object"},
                        },
                        "required": ["content"],
                    },
                },
            },
            "required": ["documents"],
        },
    }


def _tool_get_status() -> Dict[str, Any]:
    return {
        "name": "get_status",
        "description": "Report PebbleMind health: model, backend, RAG and cache state.",
        "inputSchema": {"type": "object", "properties": {}},
    }


def _resource_status() -> Dict[str, Any]:
    return {
        "uri": "pebblemind://status",
        "name": "PebbleMind status",
        "description": "Live JSON status of the local assistant",
        "mimeType": "application/json",
    }


class MCPServer:
    """JSON-RPC 2.0 MCP server over stdio, backed by a PebbleMind app."""

    def __init__(self, app=None):
        self.app = app

    # ------------------------------------------------------------------ app
    async def _ensure_app(self):
        if self.app is not None:
            return self.app
        from .pebblemind_app import create_pebblemind

        self.app = await create_pebblemind()
        return self.app

    # ----------------------------------------------------------- dispatch
    async def handle(
        self,
        msg: Dict[str, Any],
        notify: Optional[Any] = None,
    ) -> Optional[Dict[str, Any]]:
        """Handle one JSON-RPC request; returns response or None (notification).

        ``notify`` is an async callback used to emit server notifications
        (e.g. streaming progress) while a request is in flight.
        """
        method = msg.get("method", "")
        msg_id = msg.get("id")
        params = msg.get("params") or {}

        if method == "initialize":
            return self._result(
                msg_id,
                {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {"tools": {}, "resources": {}},
                    "serverInfo": MCP_SERVER_INFO,
                },
            )
        # notifications (no id) never get a response
        if msg_id is None:
            return None
        if method == "ping":
            return self._result(msg_id, {})
        if method == "tools/list":
            return self._result(
                msg_id,
                {
                    "tools": [
                        _tool_chat(),
                        _tool_ask_documents(),
                        _tool_add_documents(),
                        _tool_get_status(),
                    ]
                },
            )
        if method == "tools/call":
            return self._result(msg_id, await self._call_tool(params, notify=notify))
        if method == "resources/list":
            return self._result(msg_id, {"resources": [_resource_status()]})
        if method == "resources/read":
            if params.get("uri") == "pebblemind://status":
                app = await self._ensure_app()
                status = await app.get_status()
                return self._result(
                    msg_id,
                    {
                        "contents": [
                            {
                                "uri": "pebblemind://status",
                                "mimeType": "application/json",
                                "text": json.dumps(status, indent=2, default=str),
                            }
                        ]
                    },
                )
            return self._error(msg_id, -32602, f"Unknown resource: {params.get('uri')}")
        return self._error(msg_id, -32601, f"Method not found: {method}")

    async def _call_tool(self, params: Dict[str, Any], notify: Optional[Any] = None) -> Dict[str, Any]:
        name = params.get("name", "")
        args = params.get("arguments") or {}
        try:
            meta = params.get("_meta") or {}
            progress_token = meta.get("progressToken")
            if name == "chat" and progress_token is not None and notify is not None:
                result = await self._run_chat_streaming(args, progress_token, notify)
            else:
                result = await self._run_tool(name, args)
            text = result if isinstance(result, str) else json.dumps(result, indent=2, default=str)
            return {"content": [{"type": "text", "text": text}], "isError": False}
        except Exception as e:  # tool failures are reported, not fatal
            logger.exception("MCP tool %s failed", name)
            return {"content": [{"type": "text", "text": f"Error: {e}"}], "isError": True}

    async def _run_chat_streaming(self, args: Dict[str, Any], progress_token: Any, notify: Any) -> str:
        """Stream chat tokens as MCP progress notifications; returns full text."""
        import time as _time

        app = await self._ensure_app()
        message_text = args.get("message", "")
        use_rag = bool(args.get("use_rag", True))
        enhanced, context = await app.prepare_generation_inputs(
            message_text, use_rag=use_rag, use_memory=False,
        )
        if app.llm_engine is None:
            raise RuntimeError("No LLM engine available")
        start_time = _time.time()
        parts: list = []
        count = 0
        async for token in app.llm_engine.generate_stream(enhanced, context=context):
            parts.append(token)
            count += 1
            await notify({
                "progressToken": progress_token,
                "progress": count,
                "message": token,
            })
        response = "".join(parts)
        try:
            await app.finalize_interaction(
                message_text, response, use_memory=True,
                learn_from_interaction=True, memory_importance=0.6,
                start_time=start_time,
            )
        except Exception as e:
            logger.debug("finalize_interaction failed: %s", e)
        return response

    async def _run_tool(self, name: str, args: Dict[str, Any]):
        app = await self._ensure_app()
        if name == "chat":
            return await app.query(
                args.get("message", ""),
                use_rag=bool(args.get("use_rag", True)),
            )
        if name == "ask_documents":
            k = int(args.get("k", 3))
            question = args.get("question", "")
            if app.rag_system is None:
                return "No document store available (RAG disabled)."
            hits = await app.rag_system.search(question, k=k)
            if not hits:
                return "No matching documents. Add documents first (add_documents tool)."
            lines = []
            for i, h in enumerate(hits, 1):
                lines.append(f"[{i}] (score {h.get('score', 0):.3f}) {h.get('content', '')}")
            return "\n\n".join(lines)
        if name == "add_documents":
            docs = args.get("documents") or []
            if not docs:
                return "No documents provided."
            await app.add_documents(docs)
            return f"Added {len(docs)} document(s) to the local store."
        if name == "get_status":
            return await app.get_status()
        return {"error": f"Unknown tool: {name}", "available": ["chat", "ask_documents", "add_documents", "get_status"]}

    # ------------------------------------------------------------ plumbing
    @staticmethod
    def _result(msg_id: Any, result: Any) -> Dict[str, Any]:
        return {"jsonrpc": "2.0", "id": msg_id, "result": result}

    @staticmethod
    def _error(msg_id: Any, code: int, message: str) -> Dict[str, Any]:
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}

    async def serve_stdio(self) -> None:
        """Read newline-delimited JSON-RPC from stdin, write responses to stdout."""
        loop = asyncio.get_running_loop()
        reader = asyncio.StreamReader()
        await loop.connect_read_pipe(lambda: asyncio.StreamReaderProtocol(reader), sys.stdin.buffer)

        writer = None
        try:
            transport, protocol = await loop.connect_write_pipe(asyncio.streams.FlowControlMixin, sys.stdout.buffer)
            writer = asyncio.StreamWriter(transport, protocol, None, loop)
        except (NotImplementedError, OSError):  # stdout may not support connect_write_pipe
            writer = None

        while True:
            line = await reader.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue

            async def _notify(payload: Dict[str, Any]) -> None:
                out = json.dumps(
                    {"jsonrpc": "2.0", "method": "notifications/progress", "params": payload},
                    separators=(",", ":"),
                ) + "\n"
                if writer is not None:
                    writer.write(out.encode())
                    await writer.drain()
                else:
                    sys.stdout.write(out)
                    sys.stdout.flush()

            resp = await self.handle(msg, notify=_notify)
            if resp is not None:
                out = json.dumps(resp, separators=(",", ":")) + "\n"
                if writer is not None:
                    writer.write(out.encode())
                    await writer.drain()
                else:
                    sys.stdout.write(out)
                    sys.stdout.flush()


async def main() -> None:
    server = MCPServer()
    await server.serve_stdio()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    # Hard-exit to avoid the ggml Metal exit-time teardown abort
    # (GGML_ASSERT([rsets->data count] == 0) — ggml-org/llama.cpp#17869).
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)
