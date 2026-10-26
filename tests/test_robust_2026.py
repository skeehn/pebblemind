"""Five robust end-to-end tests added October 2026.

These are REAL end-to-end tests: they use the actual downloaded GGUF models,
the actual embedding backends, the actual CLI, API server and MCP protocol.
They are marked `robust` and `integration` and skip cleanly when the hardware
artifacts (models, running Ollama, internet) are unavailable, so CI stays green.

Run:   python -m pytest tests/test_robust_2026.py -v
Skip:  python -m pytest -m "not robust"
"""

import asyncio
import json
import os
import resource
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

from pebblemind.config import Config, LLMConfig, ToolsConfig
from pebblemind.core.llm import LLMEngine
from pebblemind.core.backends import ollama_is_available

REPO = Path(__file__).resolve().parent.parent
PY = sys.executable
MODELS_15B = REPO / "models" / "qwen2.5-1.5b-instruct-q4_k_m.gguf"
MODELS_7B = REPO / "models" / "qwen2.5-7b-instruct-q4_k_m.gguf"
BENCH_DIR = REPO / "data" / "benchmarks"

pytestmark = [pytest.mark.robust, pytest.mark.integration]

needs_15b = pytest.mark.skipif(not MODELS_15B.exists(), reason="1.5B GGUF not downloaded")
needs_ollama = pytest.mark.skipif(not ollama_is_available(), reason="Ollama not running")
needs_net = pytest.mark.skipif(
    os.environ.get("PEBBLEMIND_SKIP_NET") == "1", reason="network tests disabled"
)


def _rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024)  # macOS: bytes


def _save_bench(name: str, payload: dict) -> None:
    BENCH_DIR.mkdir(parents=True, exist_ok=True)
    path = BENCH_DIR / f"{name}.json"
    path.write_text(json.dumps(payload, indent=2, default=str))
    return None


# =====================================================================
# T1 — Performance & efficiency on real models (llama.cpp Metal vs CPU,
#       Ollama, plus response-cache speedup).
# =====================================================================
@pytest.mark.needs_15b
class TestRobustPerformance:
    PROMPT = "List the first five prime numbers, one line each."

    async def _benchmark(self, engine: LLMEngine, label: str, gen_tokens: int = 96):
        t0 = time.perf_counter()
        await engine.initialize()
        init_s = time.perf_counter() - t0

        # TTFT + throughput via streaming
        tokens: list[str] = []
        t0 = time.perf_counter()
        ttft = None
        async for tok in engine.generate_stream(self.PROMPT, max_tokens=gen_tokens):
            if ttft is None and tokens == []:
                ttft = time.perf_counter() - t0
            tokens.append(tok)
        gen_s = time.perf_counter() - t0
        n_tokens = max(1, sum(len(t.split()) for t in tokens))  # word-approx
        tok_s = len(tokens) / gen_s if gen_s > 0 else 0.0
        return {
            "label": label,
            "backend": engine.backend_name,
            "init_s": round(init_s, 3),
            "ttft_s": round(ttft, 3) if ttft is not None else None,
            "tokens": len(tokens),
            "gen_s": round(gen_s, 3),
            "tokens_per_s": round(tok_s, 2),
            "rss_mb": round(_rss_mb(), 1),
        }

    @needs_15b
    async def test_real_model_speed_and_efficiency(self):
        results = []
        rss_start = _rss_mb()

        # (a) 1.5B CPU-only
        cpu = LLMEngine(LLMConfig(
            model_path=str(MODELS_15B), model_size="1.5b",
            enable_gpu_offload=False,
        ))
        results.append(await self._benchmark(cpu, "1.5B-cpu"))
        await cpu.cleanup()

        # (b) 1.5B full Metal offload
        metal = LLMEngine(LLMConfig(
            model_path=str(MODELS_15B), model_size="1.5b",
            enable_gpu_offload=True, gpu_layers=99,
        ))
        results.append(await self._benchmark(metal, "1.5B-metal-full"))
        await metal.cleanup()

        # (c) 7B Metal (the "bigger" model) — full offload fits 16GB RAM
        if MODELS_7B.exists():
            big = LLMEngine(LLMConfig(
                model_path=str(MODELS_7B), model_size="7b",
                enable_gpu_offload=True, gpu_layers=99,
                max_tokens=96,
            ))
            results.append(await self._benchmark(big, "7B-metal-full"))
            await big.cleanup()

        # (d) cache speedup on the same engine (repeat identical request)
        metal = LLMEngine(LLMConfig(model_path=str(MODELS_15B), model_size="1.5b", enable_gpu_offload=True, gpu_layers=99))
        await metal.initialize()
        t0 = time.perf_counter()
        await metal.generate(self.PROMPT, max_tokens=48)
        cold_s = time.perf_counter() - t0
        t0 = time.perf_counter()
        await metal.generate(self.PROMPT, max_tokens=48)
        warm_s = time.perf_counter() - t0
        await metal.cleanup()
        results.append({"label": "cache-check", "cold_s": round(cold_s, 3), "warm_s": round(warm_s, 3),
                        "speedup": round(cold_s / max(warm_s, 1e-6), 2)})

        _save_bench("t1_performance", {"when": time.strftime("%Y-%m-%d %H:%M:%S"), "rss_start_mb": rss_start, "results": results})

        cpu_r = next(r for r in results if r["label"] == "1.5B-cpu")
        metal_r = next(r for r in results if r["label"] == "1.5B-metal-full")
        # Robustness floors (laptop-class, CPU): at least 3 tok/s; Metal at least 5 tok/s
        assert cpu_r["tokens_per_s"] >= 3, f"CPU too slow: {cpu_r}"
        assert metal_r["tokens_per_s"] >= 5, f"Metal too slow: {metal_r}"
        assert metal_r["ttft_s"] is not None and metal_r["ttft_s"] < 10, f"TTFT too high: {metal_r}"
        # Full Metal offload should not be slower than CPU-only
        assert metal_r["tokens_per_s"] >= cpu_r["tokens_per_s"] * 0.9, (
            f"Metal offload slower than CPU: {metal_r} vs {cpu_r}"
        )
        # Efficiency: whole bench stayed under a reasonable memory envelope
        assert _rss_mb() < 8192, "RSS ballooned beyond 8GB"


# =====================================================================
# T2 — RAG accuracy with real embeddings (sentence-transformers if
#       available, hash fallback otherwise) + grounded generation.
# =====================================================================
@pytest.mark.needs_15b
class TestRobustRAGAccuracy:
    DOCS = [
        {"content": "PebbleMind is a local-first AI assistant: all inference runs on device, no cloud calls.", "metadata": {"source": "readme", "tag": "product"}},
        {"content": "The RAG pipeline uses BGE-small embeddings (384-dim) stored in SQLite with sqlite-vec.", "metadata": {"source": "how-it-works", "tag": "rag"}},
        {"content": "Response cache is an LRU with TTL; entries expire after one hour by default.", "metadata": {"source": "cache-docs", "tag": "cache"}},
        {"content": "The recommended small model for MacBooks is Qwen2.5-1.5B-Instruct quantized to Q4_K_M.", "metadata": {"source": "models", "tag": "models"}},
        {"content": "For 16GB machines the catalog recommends the 7B Q4_K_M quantization.", "metadata": {"source": "models", "tag": "models"}},
        {"content": "Voice input uses Whisper STT; output speech uses Piper TTS voices.", "metadata": {"source": "voice", "tag": "voice"}},
        {"content": "The OpenAI-compatible API server exposes /v1/chat/completions with streaming SSE.", "metadata": {"source": "api", "tag": "api"}},
        {"content": "The plugin system loads Python classes dynamically and exposes hook events.", "metadata": {"source": "plugins", "tag": "plugins"}},
        {"content": "PebbleMind is MIT licensed and runs fully offline after models are downloaded.", "metadata": {"source": "license", "tag": "product"}},
        {"content": "Embedding backend falls back automatically: sentence-transformers, then Ollama, then hash.", "metadata": {"source": "rag", "tag": "rag"}},
        {"content": "Qwen3 models support hybrid thinking mode toggled per request.", "metadata": {"source": "models", "tag": "models"}},
        {"content": "Error handling retries failures with exponential backoff and jitter.", "metadata": {"source": "reliability", "tag": "reliability"}},
    ]
    QUESTIONS = [
        ("Which embedding dimension does the RAG system use?", "readme"),
        ("What cache eviction policy does PebbleMind use?", "cache-docs"),
        ("Which model is recommended for 16GB RAM machines?", "models"),
        ("What license does PebbleMind use?", "license"),
        ("What speech technology handles text-to-speech output?", "voice"),
        ("Which endpoint serves chat completions?", "api"),
        ("How does the embedding backend degrade when deps are missing?", "rag"),
        ("What retry strategy does error handling use?", "reliability"),
    ]

    @needs_15b
    async def test_rag_retrieval_accuracy_and_grounded_answer(self):
        from pebblemind.rag.system import RAGSystem
        from pebblemind.config import RAGConfig

        tmp_db = REPO / "data" / f"ragtest_{os.getpid()}.db"
        cfg = RAGConfig(
            embedding_backend="auto",           # real embeddings when installed
            vector_db_path=str(tmp_db),
            chunk_size=256, chunk_overlap=0, max_results=3,
        )
        rag = RAGSystem(cfg)
        await rag.initialize()
        emb_kind = type(rag.embedding_model).__name__

        await rag.add_documents(self.DOCS)

        top1, top3 = 0, 0
        details = []
        for q, expected_src in self.QUESTIONS:
            hits = await rag.search(q, k=3)
            srcs = [h.get("metadata", {}).get("source") for h in hits]
            ok1 = bool(hits) and srcs[0] == expected_src
            ok3 = expected_src in srcs
            top1 += ok1
            top3 += ok3
            details.append({"q": q, "expected": expected_src, "got": srcs, "top1": ok1})
        _save_bench("t2_rag_accuracy", {
            "embedding_backend": emb_kind,
            "top1": top1, "top3": top3, "total": len(self.QUESTIONS),
            "details": details,
        })

        # Accuracy gates: retrieval must actually work, not just not crash.
        if emb_kind != "HashEmbedding":
            assert top3 / len(self.QUESTIONS) >= 0.75, f"top-3 hit rate too low with {emb_kind}: {details}"
            assert top1 / len(self.QUESTIONS) >= 0.5, f"top-1 hit rate too low with {emb_kind}: {details}"
        else:
            # Hash fallback should still retrieve something reasonable
            assert top3 / len(self.QUESTIONS) >= 0.5, f"hash retrieval too weak: {details}"

        # Grounded generation: real LLM answers from retrieved context
        if MODELS_15B.exists():
            engine = LLMEngine(LLMConfig(model_path=str(MODELS_15B), model_size="1.5b", enable_gpu_offload=True, gpu_layers=99))
            await engine.initialize()
            hits = await rag.search("What license does PebbleMind use?", k=2)
            context = [h.get("content", "") for h in hits]
            answer = await engine.generate(
                "Answer in at most 12 words using only the context: what license does PebbleMind use?",
                context=context,
            )
            await engine.cleanup()
            assert "mit" in answer.lower(), f"Answer not grounded: {answer!r}"
        try:
            tmp_db.unlink(missing_ok=True)
        except Exception:
            pass


# =====================================================================
# T3 — Reliability & concurrency: parallel queries, cache races,
#       eviction stress, retry/backoff, rate limiter.
# =====================================================================
class TestRobustReliabilityConcurrency:
    async def test_concurrency_cache_and_retries(self):
        from pebblemind.cache.response_cache import ResponseCache
        from pebblemind.api.server import RateLimiter

        # (a) Parallel cache hammering — no race corruption
        cache = ResponseCache(max_size=200, max_memory_mb=10)
        async def hammer(i):
            await cache.set(f"k{i % 20}", {"v": i, "pad": "x" * 100})
            value, hit = await cache.get(f"k{(i * 7) % 20}")
            return value is None or isinstance(value, dict)
        results = await asyncio.gather(*[hammer(i) for i in range(200)])
        assert all(results), "cache corrupted under concurrent access"
        stats = await cache.get_stats()
        assert stats["current_size"] > 0

        # (b) LRU eviction stress: 500 inserts into 50-slot cache keeps newest
        small = ResponseCache(max_size=50, max_memory_mb=100)
        for i in range(500):
            await small.set(f"e{i}", i)
        newest, hit_new = await small.get("e499")
        oldest, _ = await small.get("e0")
        assert newest == 499 and hit_new, "newest entry evicted incorrectly"
        assert oldest is None, "oldest entry survived (LRU broken)"
        sstats = await small.get_stats()
        assert sstats["current_size"] <= 50, f"cache overflowed: {sstats}"

        # (c) Retry with backoff under injected failures
        from pebblemind.utils import error_handler as eh_mod

        attempts = {"n": 0}

        @eh_mod.with_retry(max_retries=3, retryable_exceptions=(ConnectionError,))
        async def flaky():
            attempts["n"] += 1
            if attempts["n"] < 3:
                raise ConnectionError("injected failure")
            return "ok"

        assert await flaky() == "ok"
        assert attempts["n"] == 3, f"expected 3 attempts, got {attempts['n']}"

        # (d) Concurrent generates through one engine (thread-safe path)
        if MODELS_15B.exists():
            engine = LLMEngine(LLMConfig(
                model_path=str(MODELS_15B), model_size="1.5b",
                enable_gpu_offload=True, gpu_layers=99, max_tokens=24,
            ))
            await engine.initialize()
            outs = await asyncio.gather(*[
                engine.generate(f"Reply with just the number {i}.", max_tokens=24)
                for i in range(6)
            ])
            assert len(outs) == 6 and all(isinstance(o, str) and o for o in outs), outs
            assert len(set(outs)) == 6, f"responses interleaved/corrupted: {outs}"
            await engine.cleanup()

        # (e) API rate limiter blocks after the limit
        rl = RateLimiter(requests_per_minute=3)
        allowed = [rl.is_allowed("c1") for _ in range(3)]
        blocked = rl.is_allowed("c1")
        other = rl.is_allowed("c2")
        assert all(allowed) and not blocked and other, f"rate limiter broken: {allowed=}, {blocked=}, {other=}"

        _save_bench("t3_reliability", {"status": "pass", "when": time.strftime("%Y-%m-%d %H:%M:%S")})


# =====================================================================
# T4 — CLI & API end-to-end as a real user (subprocesses + real HTTP).
# =====================================================================
@pytest.mark.needs_15b
class TestRobustCLIAPIEndToEnd:
    PY = sys.executable

    def _run_cli(self, *args, timeout=120, config_file=None):
        # --config is a group-level option: it must precede the subcommand
        cmd = [PY, "-m", "pebblemind", *args]
        if config_file:
            cmd = [PY, "-m", "pebblemind", "--config", str(config_file), *args]
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=REPO)

    def test_cli_and_openai_api_end_to_end(self, tmp_path):
        cfg_file = tmp_path / "pm.yaml"
        cfg_file.write_text(
            "llm:\n"
            f"  model_path: {MODELS_15B}\n"
            "  model_size: 1.5b\n"
            "  enable_gpu_offload: true\n"
            "  gpu_layers: 99\n"
            "rag:\n"
            "  embedding_backend: hash\n"
            "api:\n"
            "  port: 8917\n"
            "tools:\n"
            "  web_access: false\n"
        )

        # (a) doctor — health check
        r = self._run_cli("doctor", config_file=cfg_file)
        assert r.returncode == 0, r.stderr[-2000:]
        # (b) models list --catalog
        r = self._run_cli("models", "list", "--catalog")
        assert r.returncode == 0 and "qwen2.5" in (r.stdout + r.stderr).lower(), r.stderr[-2000:]
        # (c) one-shot chat with the REAL model
        t0 = time.perf_counter()
        r = self._run_cli("chat", "Answer with exactly two words: local AI", config_file=cfg_file, timeout=180)
        chat_latency = time.perf_counter() - t0
        assert r.returncode == 0, r.stderr[-2000:]
        combined = (r.stdout + r.stderr).lower()
        assert any(w in combined for w in ("local", "ai")), f"no plausible answer: {combined[-400:]}"
        assert chat_latency < 120, f"chat too slow: {chat_latency:.1f}s"

        # (d) OpenAI-compatible API server
        port = 8917
        env = dict(os.environ)
        env["PEBBLEMIND_CONFIG"] = str(cfg_file)
        proc = subprocess.Popen(
            [PY, "-m", "pebblemind.api.server"],
            cwd=REPO, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        try:
            base = f"http://localhost:{port}"
            health = None
            for _ in range(90):
                try:
                    health = httpx.get(f"{base}/health", timeout=2)
                    break
                except Exception:
                    time.sleep(1)
            assert health is not None and health.status_code == 200, f"API never came up"
            body = {"model": "pebblemind", "messages": [{"role": "user", "content": "Reply with one word: ready"}], "max_tokens": 16}
            rr = httpx.post(f"{base}/v1/chat/completions", json=body, timeout=180)
            assert rr.status_code == 200, rr.text[:500]
            data = rr.json()
            assert "choices" in data and data["choices"], f"bad completion: {data}"
            content = data["choices"][0]["message"]["content"]
            assert isinstance(content, str) and content.strip(), "empty completion"

            # (e) streaming SSE
            with httpx.stream("POST", f"{base}/v1/chat/completions", json={**body, "stream": True}, timeout=180) as s:
                assert s.status_code == 200
                chunks = [line for line in s.iter_lines() if line.startswith("data: ")]
            assert any("[DONE]" in c for c in chunks), "stream did not terminate with [DONE]"
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except Exception:
                proc.kill()

        _save_bench("t4_cli_api", {
            "chat_latency_s": round(chat_latency, 2),
            "api": "ok", "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        })


# =====================================================================
# T5 — MCP round-trip (server + client) and web access tools.
# =====================================================================
class TestRobustMCPAndWeb:
    @needs_15b
    def test_mcp_server_speaks_protocol(self, tmp_path):
        cfg_file = tmp_path / "pm.yaml"
        cfg_file.write_text(
            "llm:\n"
            f"  model_path: {MODELS_15B}\n"
            "  model_size: 1.5b\n"
            "  enable_gpu_offload: true\n"
            "  gpu_layers: 99\n"
            "rag:\n"
            "  embedding_backend: hash\n"
        )
        proc = subprocess.Popen(
            [PY, "-m", "pebblemind.mcp_server"],
            cwd=REPO, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True,
        )

        def send(payload):
            assert proc.stdin is not None
            proc.stdin.write(json.dumps(payload) + "\n")
            proc.stdin.flush()
            assert proc.stdout is not None
            line = proc.stdout.readline()
            if not line:
                err = proc.stderr.read() if proc.stderr else ""
                raise AssertionError(f"MCP server produced no response. stderr: {err[-2000:]}")
            return json.loads(line)

        try:
            # 1. initialize handshake
            init = send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                "protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "test", "version": "0"}
            }})
            assert "serverInfo" in init["result"] and init["result"]["serverInfo"]["name"] == "pebblemind"
            # 2. initialized notification (no response expected)
            proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
            proc.stdin.flush()
            # 3. tools/list
            tools = send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
            names = {t["name"] for t in tools["result"]["tools"]}
            assert {"chat", "ask_documents", "add_documents", "get_status"} <= names, names
            # 4. tools/call chat (real model inside)
            t0 = time.perf_counter()
            chat = send({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {
                "name": "chat", "arguments": {"message": "Reply with exactly: mcp works", "use_rag": False}
            }})
            mcp_chat_s = time.perf_counter() - t0
            body = chat["result"]
            assert body["isError"] is False
            assert isinstance(body["content"][0]["text"], str) and body["content"][0]["text"].strip(), body
            # 5. add_documents + ask_documents round-trip
            send({"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {
                "name": "add_documents",
                "arguments": {"documents": [{"content": "The launch code is PEBBLE-42.", "metadata": {"source": "secret"}}]},
            }})
            ask = send({"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {
                "name": "ask_documents", "arguments": {"question": "What is the launch code?", "k": 2}
            }})
            atext = ask["result"]["content"][0]["text"]
            assert "PEBBLE-42" in atext, f"RAG via MCP failed to retrieve: {atext[:300]}"
            # 6. status resource
            res = send({"jsonrpc": "2.0", "id": 6, "method": "resources/read", "params": {"uri": "pebblemind://status"}})
            status_text = res["result"]["contents"][0]["text"]
            assert "model" in status_text.lower()
            _save_bench("t5_mcp", {"chat_latency_s": round(mcp_chat_s, 2), "status": "pass"})
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except Exception:
                proc.kill()

    def test_mcp_client_calls_external_server(self):
        from pebblemind.mcp_client import MCPClientManager

        echo = REPO / "tests" / "fixtures" / "echo_mcp_server.py"

        async def flow():
            mgr = MCPClientManager.from_config({"echo": {"command": [PY, str(echo)], "timeout": 20}})
            await mgr.start()
            try:
                tools = await mgr.list_tools("echo")
                assert any(t["name"] == "echo" for t in tools["echo"])
                out = await mgr.call_tool("echo", "echo", {"text": "pebble"})
                assert out == "echo:pebble", out
                return True
            finally:
                await mgr.stop()

        assert asyncio.run(flow())

    @staticmethod
    def _py():
        return sys.executable

    @needs_net
    def test_web_access_tools(self):
        from pebblemind.web_tools import web_fetch, web_search, is_valid_url

        # SSRF guard
        assert not is_valid_url("http://localhost/x")
        assert not is_valid_url("http://127.0.0.1/x")
        assert not is_valid_url("http://192.168.1.5/x")
        assert is_valid_url("https://example.com/")

        # Probe connectivity first (offline machines skip)
        try:
            httpx.get("https://example.com", timeout=6)
        except Exception as e:
            pytest.skip(f"no internet: {e}")

        page = asyncio.run(web_fetch("https://example.com"))
        assert page["status"] == 200 and "Example Domain" in (page["title"] + page["content"])
        try:
            results = asyncio.run(web_search("PebbleMind local AI assistant github"))
        except Exception as e:
            pytest.skip(f"search engine unavailable: {e}")
        assert results and all("url" in r for r in results), results
        _save_bench("t5_web", {"fetch": "ok", "results": len(results)})
