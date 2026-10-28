"""MCP client: lets PebbleMind call external MCP servers (tools/resources).

Supports the stdio transport (spawn a server process and speak JSON-RPC 2.0
newline-delimited over its stdin/stdout) — the transport used by Claude
Desktop, Cursor, and most local MCP servers. Also supports HTTP servers that
accept JSON-RPC POSTs at an endpoint.

Example:
    mgr = MCPClientManager.from_config({"filesystem": {"command": ["npx", "-y", "@modelcontextprotocol/server-filesystem", "/tmp"]}})
    await mgr.start()
    tools = await mgr.list_tools()
    result = await mgr.call_tool("filesystem", "read_file", {"path": "/tmp/x"})
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

MCP_PROTOCOL_VERSION = "2025-06-18"


@dataclass
class MCPServerConfig:
    """How to reach one MCP server."""
    name: str
    command: Optional[List[str]] = None      # stdio transport: executable + args
    url: Optional[str] = None                # http transport: endpoint URL
    env: Dict[str, str] = field(default_factory=dict)
    timeout: float = 30.0


class MCPServerSession:
    """A live connection to one MCP server (stdio or HTTP)."""

    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.name = config.name
        self.proc: Optional[asyncio.subprocess.Process] = None
        self._next_id = 0
        self.server_info: Dict[str, Any] = {}
        self.tools: List[Dict[str, Any]] = []

    # -------------------------------------------------------------- stdio
    async def start(self) -> None:
        if self.config.command:
            self.proc = await asyncio.create_subprocess_exec(
                *self.config.command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
                env={**dict(__import__("os").environ), **self.config.env},
                limit=64 * 1024 * 1024,  # tool results can ride on one big JSON line
            )
        try:
            init = await self._request(
                "initialize",
                {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "pebblemind", "version": "0.1.0"},
                },
            )
            if init is None:
                raise RuntimeError(f"MCP server '{self.name}' did not respond to initialize")
            self.server_info = init.get("serverInfo", init)
            await self._notify("notifications/initialized")
            try:
                listed = await self._request("tools/list", {})
                self.tools = (listed or {}).get("tools", [])
            except Exception as e:  # tools are optional per spec
                logger.debug("tools/list failed for %s: %s", self.name, e)
                self.tools = []
        except BaseException:
            # Handshake failed — don't leak the spawned child process.
            await self.stop()
            raise
        logger.info("MCP session '%s' ready: %d tools", self.name, len(self.tools))

    async def stop(self) -> None:
        """Terminate the server session. Idempotent; never raises for an
        already-exited process — a teardown failure must not mask the real
        cause (e.g. the handshake error that triggered this stop)."""
        proc, self.proc = self.proc, None  # clear first: failures can't wedge state
        if proc is None:
            return
        try:
            await self._notify("shutdown")
        except Exception:
            pass
        try:
            if proc.returncode is None:  # None = still running
                proc.terminate()
                await asyncio.wait_for(proc.wait(), timeout=5)
            else:
                await proc.wait()
        except Exception:
            try:
                proc.kill()
                await proc.wait()
            except ProcessLookupError:
                pass  # exited on its own between the checks

    # -------------------------------------------------------------- wire
    async def _send(self, payload: Dict[str, Any]) -> None:
        if not self.proc or not self.proc.stdin:
            raise RuntimeError(f"MCP server '{self.name}' not running")
        self.proc.stdin.write((json.dumps(payload, separators=(",", ":")) + "\n").encode())
        await self.proc.stdin.drain()

    async def _read_response(self, want_id: int, timeout: float, on_progress=None) -> Optional[Dict[str, Any]]:
        assert self.proc and self.proc.stdout
        while True:
            line = await asyncio.wait_for(self.proc.stdout.readline(), timeout=timeout)
            if not line:
                return None
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if on_progress and msg.get("method") == "notifications/progress":
                await on_progress(msg.get("params") or {})
                continue
            if msg.get("id") == want_id:
                return msg

    async def _request(self, method: str, params: Dict[str, Any], on_progress=None) -> Optional[Dict[str, Any]]:
        self._next_id += 1
        rid = self._next_id
        payload = {"jsonrpc": "2.0", "id": rid, "method": method, "params": params}
        if self.config.command:  # stdio
            await self._send(payload)
            resp = await self._read_response(rid, self.config.timeout, on_progress=on_progress)
        else:  # http
            resp = await self._http_request(payload)
        if resp is None:
            return None
        if "error" in resp:
            raise RuntimeError(f"MCP error ({method}): {resp['error']}")
        return resp.get("result")

    async def _notify(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        payload = {"jsonrpc": "2.0", "method": method, "params": params or {}}
        if self.config.command:
            await self._send(payload)
        else:
            await self._http_request(payload)

    async def _http_request(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.config.url:
            raise RuntimeError(f"MCP server '{self.name}' has no command or url")
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            r = await client.post(self.config.url, json=payload)
            r.raise_for_status()
            if not r.content.strip():
                return None
            return r.json()

    # ------------------------------------------------------------- public
    async def list_tools(self) -> List[Dict[str, Any]]:
        return self.tools

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any], stream: bool = False, on_progress=None) -> str:
        """Call a tool. With ``stream=True`` (stdio servers), a progress token is
        attached and ``on_progress(params)`` fires for each progress notification.
        """
        params: Dict[str, Any] = {"name": tool_name, "arguments": arguments}
        if stream:
            params["_meta"] = {"progressToken": f"pt-{self._next_id + 1}"}
        result = await self._request("tools/call", params, on_progress=on_progress)
        if result is None:
            raise RuntimeError(f"MCP server '{self.name}' returned no result")
        if result.get("isError"):
            parts = result.get("content", [])
            text = " ".join(p.get("text", "") for p in parts if isinstance(p, dict))
            raise RuntimeError(f"MCP tool '{tool_name}' failed: {text}")
        parts = result.get("content", [])
        texts = []
        for p in parts:
            if isinstance(p, dict) and p.get("type") == "text":
                texts.append(p.get("text", ""))
        return "\n".join(texts)

    async def read_resource(self, uri: str) -> str:
        result = await self._request("resources/read", {"uri": uri})
        contents = (result or {}).get("contents", [])
        return "\n".join(c.get("text", "") for c in contents if isinstance(c, dict))


class MCPClientManager:
    """Owns several MCP server sessions, keyed by name."""

    def __init__(self, configs: Optional[List[MCPServerConfig]] = None):
        self.configs = {c.name: c for c in (configs or [])}
        self.sessions: Dict[str, MCPServerSession] = {}

    @classmethod
    def from_config(cls, spec: Dict[str, Dict[str, Any]]) -> "MCPClientManager":
        configs = []
        for name, raw in spec.items():
            cmd = raw.get("command")
            if isinstance(cmd, str):
                cmd = cmd.split()
            configs.append(
                MCPServerConfig(
                    name=name,
                    command=cmd,
                    url=raw.get("url"),
                    env=raw.get("env") or {},
                    timeout=float(raw.get("timeout", 30)),
                )
            )
        return cls(configs)

    async def start(self) -> None:
        for name in list(self.configs):
            if name not in self.sessions:
                session = MCPServerSession(self.configs[name])
                await session.start()
                self.sessions[name] = session

    async def stop(self) -> None:
        """Stop every session; one dead server must not block the rest."""
        for name, session in self.sessions.items():
            try:
                await session.stop()
            except Exception as e:
                logger.warning("MCP session '%s' failed to stop cleanly: %s", name, e)
        self.sessions.clear()

    def names(self) -> List[str]:
        return list(self.sessions)

    def all_tools(self) -> Dict[str, List[Dict[str, Any]]]:
        return {n: list(s.tools) for n, s in self.sessions.items()}

    async def list_tools(self, server: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        if server:
            return {server: await self.sessions[server].list_tools()}
        return {n: await s.list_tools() for n, s in self.sessions.items()}

    async def call_tool(self, server: str, tool: str, arguments: Dict[str, Any]) -> str:
        session = self.sessions.get(server)
        if not session:
            raise KeyError(f"MCP server '{server}' not running. Available: {list(self.sessions)}")
        return await session.call_tool(tool, arguments)

    async def read_resource(self, server: str, uri: str) -> str:
        return await self.sessions[server].read_resource(uri)
