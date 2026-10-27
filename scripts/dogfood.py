#!/usr/bin/env python3
"""Dogfood: exercise PebbleMind exactly like a real user, with timings.

Prerequisites: a downloaded GGUF (models/qwen2.5-1.5b-instruct-q4_k_m.gguf by
default) and either Ollama running or llama-cpp-python built (METAL=1).
Optionally set PEBBLEMIND_DOGFOOD_MODEL=/path/to/other.gguf.

Usage:
    python scripts/dogfood.py
"""

import asyncio
import json
import os
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from pebblemind.config import Config  # noqa: E402
from pebblemind.core.backends import ollama_is_available  # noqa: E402


def pick_config(tmp: Path) -> Config:
    cfg = Config()
    cfg.data_dir = str(tmp / "data")
    cfg.cache_dir = str(tmp / "cache")
    cfg.rag.vector_db_path = str(tmp / "vectors.db")
    cfg.rag.embedding_backend = "hash"  # deterministic, zero downloads
    model = os.environ.get("PEBBLEMIND_DOGFOOD_MODEL")
    if not model and ollama_is_available():
        cfg.llm.backend = "ollama"
        cfg.llm.ollama_model = "qwen2.5:1.5b"
    else:
        model = model or str(REPO / "models" / "qwen2.5-1.5b-instruct-q4_k_m.gguf")
        if not Path(model).exists():
            print("FATAL: no model — download a GGUF or start Ollama")
            raise SystemExit(1)
        cfg.llm.model_path = model
        cfg.llm.model_size = "1.5b"
        cfg.llm.enable_gpu_offload = True
        cfg.llm.gpu_layers = 99
    return cfg


async def main() -> None:
    timings = {}

    def mark(name: str, t0: float) -> None:
        timings[name] = round(time.perf_counter() - t0, 2)
        print(f"  ✅ {name}: {timings[name]}s")

    with tempfile.TemporaryDirectory(prefix="pebblemind_dogfood_") as td:
        tmp = Path(td)
        cfg = pick_config(tmp)

        from pebblemind.pebblemind_app import PebbleMind

        app = PebbleMind(cfg)

        t0 = time.perf_counter()
        await app.initialize()
        mark("initialize", t0)

        # --- 1. ingest the project's own docs (real use: private doc Q&A)
        docs = []
        for name in ["QUICKSTART.md", "HOW_IT_WORKS.md", "SECURITY.md", "README.md"]:
            p = REPO / name
            if p.exists():
                docs.append({"content": p.read_text(), "metadata": {"source": name}})
        t0 = time.perf_counter()
        await app.add_documents(docs)
        mark(f"ingest_{len(docs)}_docs", t0)

        # --- 2. RAG retrieval on real project docs
        t0 = time.perf_counter()
        hits = await app.rag_system.search("How do I start the OpenAI-compatible API server?", k=2)
        rag_s = time.perf_counter() - t0
        top = hits[0].get("content", "")[:90].replace("\n", " ")
        print(f"  🔎 top passage ({rag_s:.2f}s): {top}")
        timings["rag_search"] = round(rag_s, 2)
        assert hits, "RAG search returned nothing"

        # --- 3. grounded chat (RAG -> LLM)
        t0 = time.perf_counter()
        answer = await app.query(
            "In one sentence: how do I start the OpenAI-compatible API server?",
            use_rag=True, use_tools=False, use_memory=False, enhance_reasoning=False,
        )
        mark("rag_grounded_chat", t0)
        print(f"  💬 {answer[:140]}")

        # --- 4. plain chat (no RAG)
        t0 = time.perf_counter()
        plain = await app.query(
            "Reply with exactly: dogfood ok",
            use_rag=False, use_tools=False, use_memory=False, enhance_reasoning=False,
        )
        mark("plain_chat", t0)
        print(f"  💬 {plain[:80]}")

        # --- 5. caching: same request twice
        q = "What is 2+2? Answer with just the number."
        t0 = time.perf_counter()
        await app.query(q, use_rag=False, use_tools=False, use_memory=False, enhance_reasoning=False)
        cold = time.perf_counter() - t0
        t0 = time.perf_counter()
        await app.query(q, use_rag=False, use_tools=False, use_memory=False, enhance_reasoning=False)
        warm = time.perf_counter() - t0
        timings["cache_cold_warm"] = f"{cold:.2f}s / {warm:.2f}s"
        print(f"  ⚡ cache cold={cold:.2f}s warm={warm:.2f}s")

        # --- 6. OpenAI-compatible API server (real HTTP)
        t0 = time.perf_counter()
        import httpx
        from pebblemind.api.server import APIServer

        port = 8931
        app.config.api.port = port
        server = APIServer(config=app.config.api, pebblemind=app)
        serve_task = asyncio.create_task(server.start())
        await asyncio.sleep(1.5)
        r = await httpx.AsyncClient(timeout=180).post(
            f"http://localhost:{port}/v1/chat/completions",
            json={"model": "pebblemind", "messages": [{"role": "user", "content": "Reply with: api ok"}], "max_tokens": 16},
        )
        mark("api_openai_completion", t0)
        assert r.status_code == 200 and r.json()["choices"], r.text[:300]
        print(f"  🌐 API says: {r.json()['choices'][0]['message']['content'][:60]!r}")
        serve_task.cancel()
        try:
            await serve_task
        except asyncio.CancelledError:
            pass  # expected on shutdown

        # --- 7. MCP round-trip with streaming progress
        t0 = time.perf_counter()
        from pebblemind.mcp_server import MCPServer

        mcp = MCPServer(app=app)
        progress: list = []

        async def notify(p):
            progress.append(p)

        result = await mcp.handle(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
                "name": "chat",
                "arguments": {"message": "Reply with: mcp ok", "use_rag": False},
                "_meta": {"progressToken": "dog"},
            }},
            notify=notify,
        )
        mark("mcp_streaming_chat", t0)
        text = result["result"]["content"][0]["text"]
        assert "isError" not in result["result"] or result["result"]["isError"] is False
        print(f"  🔌 MCP streamed {len(progress)} chunks -> {text[:40]!r}")

        # --- 8. stop
        t0 = time.perf_counter()
        await app.stop()
        mark("stop", t0)

        print("\n== DOGFOOD TIMINGS ==")
        print(json.dumps(timings, indent=2))
        print("ALL DOGFOOD CHECKS PASSED")


if __name__ == "__main__":
    asyncio.run(main())
