#!/usr/bin/env python3
"""Cross-backend generation speed benchmark — real tokens, not words.

Usage: python scripts/bench_speed.py
Measures wall-clock tokens/second for the bundled llama.cpp backend
(Metal + flash attention vs CPU-only) and Ollama models, then writes
data/benchmarks/speed_<date>.json.

Ollama timings come from the server's own eval_count/eval_duration;
llama.cpp timings count tokens against wall-clock around the engine call
(prompt budget, chat template and engine lock all included).
"""

import asyncio
import json
import sys
import time
from datetime import date
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from pebblemind.config import LLMConfig
from pebblemind.core.llm import LLMEngine

PROMPT = "Explain, in plain language, why the sky is blue."
N_TOKENS = 96
M15 = REPO / "models" / "qwen2.5-1.5b-instruct-q4_k_m.gguf"
Q3 = Path.home() / ".ollama/models/blobs/sha256-3e4cb14174460404e7a233e531675303b2fbf7749c02f91864fe311ab6344e4f"

async def bench_llamacpp(label: str, cfg: LLMConfig, results: dict) -> None:
    engine = LLMEngine(cfg)
    await engine.initialize()
    await engine.generate("Hi", max_tokens=8, temperature=0.0)  # warmup
    t0 = time.perf_counter()
    text = await engine.generate(PROMPT, max_tokens=N_TOKENS, temperature=0.0)
    wall = time.perf_counter() - t0
    ntok = len(engine.model.tokenize(text.encode("utf-8"), add_bos=False, special=False))
    await engine.cleanup()
    results[label] = {"tok_s": round(ntok / wall, 1), "tokens": ntok, "wall_s": round(wall, 2)}

async def bench_ollama(label: str, model: str, host: str, results: dict) -> None:
    async with httpx.AsyncClient(timeout=180) as client:
        payload = {"model": model, "stream": False,
                   "messages": [{"role": "user", "content": PROMPT}],
                   "options": {"num_predict": N_TOKENS, "temperature": 0.0}}
        await client.post(f"{host}/api/chat", json={**payload, "messages": payload["messages"][:1], "options": {"num_predict": 4}})
        t0 = time.perf_counter()
        r = await client.post(f"{host}/api/chat", json=payload)
        wall = time.perf_counter() - t0
        body = r.json()
    results[label] = {"tok_s": round(body["eval_count"] / (body["eval_duration"] / 1e9), 1),
                      "tokens": body["eval_count"], "wall_s": round(wall, 2)}

async def main() -> None:
    host = "http://localhost:11434"
    results: dict = {}
    await bench_llamacpp("llamacpp 1.5B Metal full offload + flash-attn (new default)",
                         LLMConfig(model_path=str(M15)), results)
    await bench_llamacpp("llamacpp 1.5B CPU-only",
                         LLMConfig(model_path=str(M15), enable_gpu_offload=False, auto_detect_gpu=False), results)
    if Q3.exists():
        await bench_llamacpp("llamacpp qwen3-4B Metal full offload + flash-attn",
                             LLMConfig(model_path=str(Q3), model_name="Qwen3-4B"), results)
    for label, model in [("ollama qwen2.5:1.5b", "qwen2.5:1.5b"), ("ollama qwen3:4b", "qwen3:4b"), ("ollama qwen2.5:7b", "qwen2.5:7b")]:
        await bench_ollama(label, model, host, results)

    out = {"date": str(date.today()), "prompt": PROMPT, "max_tokens": N_TOKENS, "results": results}
    dest = REPO / "data" / "benchmarks" / f"speed_{date.today()}.json"
    dest.write_text(json.dumps(out, indent=2) + "\n")
    for label, r in results.items():
        print(f"{label:55s} {r['tok_s']:>7} tok/s ({r['wall_s']}s wall)")
    print(f"saved -> {dest.relative_to(REPO)}")

if __name__ == "__main__":
    asyncio.run(main())
