"""Pluggable LLM backends: Ollama, llama.cpp GGUF, HuggingFace, fallback.

Ollama is the recommended path on Mac (brew install ollama) because it
handles Metal acceleration, quantized small models, and embeddings with
zero Python dependencies — just HTTP to localhost:11434.
"""
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

OLLAMA_DEFAULT_HOST = "http://localhost:11434"

# Small Mac-friendly models. Each entry: ollama tag + HF repo (+ GGUF URL).
MAC_SMALL_MODELS = {
    # ultra-light (<2GB, any MacBook Air)
    "smollm2-135m": {
        "ollama": "smollm2:135m",
        "hf": "HuggingFaceTB/SmolLM2-135M-Instruct",
        "gguf_url": "https://huggingface.co/HuggingFaceTB/smollm2-135m-instruct-gguf/resolve/main/smollm2-135m-instruct-q4_k_m.gguf",
        "size_gb": 0.2,
        "ram_gb": 2,
    },
    "smollm2-360m": {
        "ollama": "smollm2:360m",
        "hf": "HuggingFaceTB/SmolLM2-360M-Instruct",
        "gguf_url": "https://huggingface.co/HuggingFaceTB/smollm2-360m-instruct-gguf/resolve/main/smollm2-360m-instruct-q4_k_m.gguf",
        "size_gb": 0.3,
        "ram_gb": 2,
    },
    "qwen3-0.6b": {
        "ollama": "qwen3:0.6b",
        "hf": "Qwen/Qwen3-0.6B",
        "gguf_url": "https://huggingface.co/Qwen/Qwen3-0.6B-GGUF/resolve/main/Qwen3-0.6B-Q4_K_M.gguf",
        "size_gb": 0.5,
        "ram_gb": 2,
    },
    "llama3.2-1b": {
        "ollama": "llama3.2:1b",
        "hf": "meta-llama/Llama-3.2-1B-Instruct",
        "gguf_url": "https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf",
        "size_gb": 0.8,
        "ram_gb": 4,
    },
    "qwen2.5-1.5b": {
        "ollama": "qwen2.5:1.5b",
        "hf": "Qwen/Qwen2.5-1.5B-Instruct",
        "gguf_url": "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf",
        "size_gb": 1.0,
        "ram_gb": 4,
    },
    "smollm2-1.7b": {
        "ollama": "smollm2:1.7b",
        "hf": "HuggingFaceTB/SmolLM2-1.7B-Instruct",
        "gguf_url": "https://huggingface.co/HuggingFaceTB/smollm2-1.7b-instruct-gguf/resolve/main/smollm2-1.7b-instruct-q4_k_m.gguf",
        "size_gb": 1.1,
        "ram_gb": 4,
    },
    "qwen3-1.7b": {
        "ollama": "qwen3:1.7b",
        "hf": "Qwen/Qwen3-1.7B",
        "gguf_url": "https://huggingface.co/Qwen/Qwen3-1.7B-GGUF/resolve/main/Qwen3-1.7B-Q4_K_M.gguf",
        "size_gb": 1.2,
        "ram_gb": 4,
    },
    # balanced (3-4GB, 8GB RAM Macs)
    "llama3.2-3b": {
        "ollama": "llama3.2:3b",
        "hf": "meta-llama/Llama-3.2-3B-Instruct",
        "gguf_url": "https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf",
        "size_gb": 2.0,
        "ram_gb": 8,
    },
    "qwen2.5-3b": {
        "ollama": "qwen2.5:3b",
        "hf": "Qwen/Qwen2.5-3B-Instruct",
        "gguf_url": "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf",
        "size_gb": 2.0,
        "ram_gb": 8,
    },
    "phi-3-mini": {
        "ollama": "phi3:mini",
        "hf": "microsoft/Phi-3-mini-4k-instruct",
        "gguf_url": "https://huggingface.co/bartowski/Phi-3-mini-4k-instruct-GGUF/resolve/main/Phi-3-mini-4k-instruct-Q4_K_M.gguf",
        "size_gb": 2.3,
        "ram_gb": 8,
    },
    "gemma2-2b": {
        "ollama": "gemma2:2b",
        "hf": "google/gemma-2-2b-it",
        "gguf_url": "https://huggingface.co/bartowski/gemma-2-2b-it-GGUF/resolve/main/gemma-2-2b-it-Q4_K_M.gguf",
        "size_gb": 1.6,
        "ram_gb": 8,
    },
    "qwen3-4b": {
        "ollama": "qwen3:4b",
        "hf": "Qwen/Qwen3-4B",
        "gguf_url": "https://huggingface.co/Qwen/Qwen3-4B-GGUF/resolve/main/Qwen3-4B-Q4_K_M.gguf",
        "size_gb": 2.6,
        "ram_gb": 8,
    },
    # quality (4-5GB, 16GB RAM Macs)
    "qwen2.5-7b": {
        "ollama": "qwen2.5:7b",
        "hf": "Qwen/Qwen2.5-7B-Instruct",
        "gguf_url": "https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_k_m.gguf",
        "size_gb": 4.4,
        "ram_gb": 16,
    },
    "llama3-8b": {
        "ollama": "llama3:8b",
        "hf": "meta-llama/Meta-Llama-3-8B-Instruct",
        "gguf_url": "https://huggingface.co/bartowski/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf",
        "size_gb": 4.7,
        "ram_gb": 16,
    },
    "mistral-7b": {
        "ollama": "mistral:7b",
        "hf": "mistralai/Mistral-7B-Instruct-v0.3",
        "gguf_url": "https://huggingface.co/bartowski/Mistral-7B-Instruct-v0.3-GGUF/resolve/main/Mistral-7B-Instruct-v0.3-Q4_K_M.gguf",
        "size_gb": 4.4,
        "ram_gb": 16,
    },
}


def ollama_is_available(host: str = OLLAMA_DEFAULT_HOST, timeout: float = 1.5) -> bool:
    """Return True if an Ollama server answers at host."""
    try:
        import httpx

        r = httpx.get(f"{host.rstrip('/')}/api/tags", timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False


def ollama_has_model(model: str, host: str = OLLAMA_DEFAULT_HOST, timeout: float = 5.0) -> bool:
    """Return True if the model tag is already pulled in Ollama."""
    try:
        import httpx

        r = httpx.get(f"{host.rstrip('/')}/api/tags", timeout=timeout)
        if r.status_code != 200:
            return False
        names = [m.get("name", "") for m in r.json().get("models", [])]
        base = model.split(":")[0]
        return any(n == model or n.startswith(base + ":") or n == base for n in names)
    except Exception:
        return False


def ollama_chat(
    messages: List[Dict[str, str]],
    model: str,
    host: str = OLLAMA_DEFAULT_HOST,
    options: Optional[Dict[str, Any]] = None,
    timeout: float = 120.0,
) -> str:
    """Non-streaming chat via Ollama /api/chat. Raises on error."""
    import httpx

    payload: Dict[str, Any] = {"model": model, "messages": messages, "stream": False}
    if options:
        payload["options"] = options
    r = httpx.post(f"{host.rstrip('/')}/api/chat", json=payload, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    msg = data.get("message", {})
    content = msg.get("content", "")
    if not content:
        raise RuntimeError(f"Ollama returned no content: {data}")
    return content


def ollama_embed(
    texts: List[str],
    model: str = "nomic-embed-text",
    host: str = OLLAMA_DEFAULT_HOST,
    timeout: float = 60.0,
):
    """Embed via Ollama /api/embed. Returns numpy array (n, dim)."""
    import httpx

    import numpy as np

    out = []
    for t in texts:
        r = httpx.post(
            f"{host.rstrip('/')}/api/embed",
            json={"model": model, "input": t},
            timeout=timeout,
        )
        r.raise_for_status()
        data = r.json()
        emb = data.get("embeddings", [data.get("embedding", [])])[0]
        out.append(emb)
    return np.array(out, dtype=np.float32)


def recommend_model(available_ram_gb: float = 8.0) -> str:
    """Pick the biggest quality small model that fits RAM."""
    if available_ram_gb < 4:
        return "qwen2.5:1.5b"
    if available_ram_gb < 8:
        return "qwen2.5:3b"
    if available_ram_gb < 16:
        return "qwen2.5:7b"
    return "qwen2.5:7b"
