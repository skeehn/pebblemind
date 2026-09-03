"""
Model Management for PebbleMind.

Small-model-first catalog: every entry carries an Ollama tag (best Mac path),
a HuggingFace repo, and a GGUF download URL. Checksums are optional — entries
without a known sha256 skip verification instead of failing.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
import urllib.request
import hashlib

logger = logging.getLogger(__name__)


def _m(name, ollama, hf, filename, size_gb, ram_gb, speed, quality, description, use_case):
    return {
        "name": name,
        "ollama": ollama,
        "hf_repo": hf,
        "url": f"https://huggingface.co/{hf}-GGUF/resolve/main/{filename}"
        if "-GGUF" not in hf and "GGUF" not in filename else None,
        "filename": filename,
        "size_gb": size_gb,
        "ram_gb": ram_gb,
        "speed": speed,
        "quality": quality,
        "description": description,
        "use_case": use_case,
        "sha256": None,
    }


# Full small-model catalog (Ollama tag is the source of truth on Mac).
MODEL_CATALOG = {
    "smollm2-135m": {
        "name": "SmolLM2 135M (Q4)",
        "ollama": "smollm2:135m",
        "hf_repo": "HuggingFaceTB/SmolLM2-135M-Instruct",
        "url": "https://huggingface.co/HuggingFaceTB/smollm2-135m-instruct-gguf/resolve/main/smollm2-135m-instruct-q4_k_m.gguf",
        "filename": "smollm2-135m-instruct-q4_k_m.gguf",
        "size_gb": 0.2, "ram_gb": 2, "speed": "⚡⚡⚡⚡", "quality": "⭐",
        "description": "Tiny 135M model, instant on any Mac",
        "use_case": "Testing, autocomplete, ultra-low RAM",
        "sha256": None,
    },
    "smollm2-360m": {
        "name": "SmolLM2 360M (Q4)",
        "ollama": "smollm2:360m",
        "hf_repo": "HuggingFaceTB/SmolLM2-360M-Instruct",
        "url": "https://huggingface.co/HuggingFaceTB/smollm2-360m-instruct-gguf/resolve/main/smollm2-360m-instruct-q4_k_m.gguf",
        "filename": "smollm2-360m-instruct-q4_k_m.gguf",
        "size_gb": 0.3, "ram_gb": 2, "speed": "⚡⚡⚡⚡", "quality": "⭐⭐",
        "description": "Fast tiny model, great for drafts",
        "use_case": "Quick responses, testing, low-resource systems",
        "sha256": None,
    },
    "qwen3-0.6b": {
        "name": "Qwen 3 0.6B (Q4)",
        "ollama": "qwen3:0.6b",
        "hf_repo": "Qwen/Qwen3-0.6B",
        "url": "https://huggingface.co/Qwen/Qwen3-0.6B-GGUF/resolve/main/Qwen3-0.6B-Q4_K_M.gguf",
        "filename": "Qwen3-0.6B-Q4_K_M.gguf",
        "size_gb": 0.5, "ram_gb": 2, "speed": "⚡⚡⚡⚡", "quality": "⭐⭐",
        "description": "Qwen3 tiny, strong for its size",
        "use_case": "Fast chat, edge devices",
        "sha256": None,
    },
    "llama3.2-1b": {
        "name": "Llama 3.2 1B (Q4)",
        "ollama": "llama3.2:1b",
        "hf_repo": "meta-llama/Llama-3.2-1B-Instruct",
        "url": "https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf",
        "filename": "Llama-3.2-1B-Instruct-Q4_K_M.gguf",
        "size_gb": 0.8, "ram_gb": 4, "speed": "⚡⚡⚡", "quality": "⭐⭐",
        "description": "Meta 1B instruct, good instruction following",
        "use_case": "Chat, summarization on 8GB Macs",
        "sha256": None,
    },
    "qwen2.5-1.5b-q4": {
        "name": "Qwen 2.5 1.5B (Q4)",
        "ollama": "qwen2.5:1.5b",
        "hf_repo": "Qwen/Qwen2.5-1.5B-Instruct",
        "url": "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf",
        "filename": "qwen2.5-1.5b-instruct-q4_k_m.gguf",
        "size_gb": 1.0, "ram_gb": 4, "speed": "⚡⚡⚡", "quality": "⭐⭐",
        "description": "Fast, lightweight model for quick responses and testing",
        "use_case": "Quick responses, testing, low-resource systems",
        "sha256": None,
    },
    "smollm2-1.7b": {
        "name": "SmolLM2 1.7B (Q4)",
        "ollama": "smollm2:1.7b",
        "hf_repo": "HuggingFaceTB/SmolLM2-1.7B-Instruct",
        "url": "https://huggingface.co/HuggingFaceTB/smollm2-1.7b-instruct-gguf/resolve/main/smollm2-1.7b-instruct-q4_k_m.gguf",
        "filename": "smollm2-1.7b-instruct-q4_k_m.gguf",
        "size_gb": 1.1, "ram_gb": 4, "speed": "⚡⚡⚡", "quality": "⭐⭐⭐",
        "description": "Best-in-class 1.7B, beats many 3B models",
        "use_case": "Daily chat on MacBook Air",
        "sha256": None,
    },
    "qwen3-1.7b": {
        "name": "Qwen 3 1.7B (Q4)",
        "ollama": "qwen3:1.7b",
        "hf_repo": "Qwen/Qwen3-1.7B",
        "url": "https://huggingface.co/Qwen/Qwen3-1.7B-GGUF/resolve/main/Qwen3-1.7B-Q4_K_M.gguf",
        "filename": "Qwen3-1.7B-Q4_K_M.gguf",
        "size_gb": 1.2, "ram_gb": 4, "speed": "⚡⚡⚡", "quality": "⭐⭐⭐",
        "description": "Qwen3 small with hybrid reasoning",
        "use_case": "Chat + light reasoning",
        "sha256": None,
    },
    "gemma2-2b": {
        "name": "Gemma 2 2B (Q4)",
        "ollama": "gemma2:2b",
        "hf_repo": "google/gemma-2-2b-it",
        "url": "https://huggingface.co/bartowski/gemma-2-2b-it-GGUF/resolve/main/gemma-2-2b-it-Q4_K_M.gguf",
        "filename": "gemma-2-2b-it-Q4_K_M.gguf",
        "size_gb": 1.6, "ram_gb": 8, "speed": "⚡⚡⚡", "quality": "⭐⭐⭐",
        "description": "Google 2B instruct, strong quality/size",
        "use_case": "Chat, writing, Q&A",
        "sha256": None,
    },
    "llama3.2-3b": {
        "name": "Llama 3.2 3B (Q4)",
        "ollama": "llama3.2:3b",
        "hf_repo": "meta-llama/Llama-3.2-3B-Instruct",
        "url": "https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf",
        "filename": "Llama-3.2-3B-Instruct-Q4_K_M.gguf",
        "size_gb": 2.0, "ram_gb": 8, "speed": "⚡⚡", "quality": "⭐⭐⭐",
        "description": "Meta 3B, excellent all-rounder",
        "use_case": "General purpose on 8GB+ Macs",
        "sha256": None,
    },
    "qwen2.5-3b-q4": {
        "name": "Qwen 2.5 3B (Q4)",
        "ollama": "qwen2.5:3b",
        "hf_repo": "Qwen/Qwen2.5-3B-Instruct",
        "url": "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf",
        "filename": "qwen2.5-3b-instruct-q4_k_m.gguf",
        "size_gb": 2.0, "ram_gb": 8, "speed": "⚡⚡", "quality": "⭐⭐⭐",
        "description": "Balanced 3B chat + tools",
        "use_case": "Daily driver for 8GB Macs",
        "sha256": None,
    },
    "phi-3-mini": {
        "name": "Phi-3 Mini 3.8B (Q4)",
        "ollama": "phi3:mini",
        "hf_repo": "microsoft/Phi-3-mini-4k-instruct",
        "url": "https://huggingface.co/bartowski/Phi-3-mini-4k-instruct-GGUF/resolve/main/Phi-3-mini-4k-instruct-Q4_K_M.gguf",
        "filename": "Phi-3-mini-4k-instruct-Q4_K_M.gguf",
        "size_gb": 2.3, "ram_gb": 8, "speed": "⚡⚡", "quality": "⭐⭐⭐",
        "description": "Microsoft small, strong reasoning",
        "use_case": "Reasoning, math, code help",
        "sha256": None,
    },
    "qwen3-4b": {
        "name": "Qwen 3 4B (Q4)",
        "ollama": "qwen3:4b",
        "hf_repo": "Qwen/Qwen3-4B",
        "url": "https://huggingface.co/Qwen/Qwen3-4B-GGUF/resolve/main/Qwen3-4B-Q4_K_M.gguf",
        "filename": "Qwen3-4B-Q4_K_M.gguf",
        "size_gb": 2.6, "ram_gb": 8, "speed": "⚡⚡", "quality": "⭐⭐⭐⭐",
        "description": "Qwen3 4B hybrid reasoning",
        "use_case": "Best quality under 3GB",
        "sha256": None,
    },
    "qwen2.5-7b-q4": {
        "name": "Qwen 2.5 7B (Q4)",
        "ollama": "qwen2.5:7b",
        "hf_repo": "Qwen/Qwen2.5-7B-Instruct",
        "url": "https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_k_m.gguf",
        "filename": "qwen2.5-7b-instruct-q4_k_m.gguf",
        "size_gb": 4.4, "ram_gb": 16, "speed": "⚡⚡", "quality": "⭐⭐⭐⭐",
        "description": "Balanced performance and quality, recommended default",
        "use_case": "General purpose, good balance of speed and quality",
        "sha256": None,
    },
    "llama-3-8b-q4": {
        "name": "Llama 3 8B (Q4)",
        "ollama": "llama3:8b",
        "hf_repo": "meta-llama/Meta-Llama-3-8B-Instruct",
        "url": "https://huggingface.co/bartowski/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf",
        "filename": "llama-3-8b-instruct-q4.gguf",
        "size_gb": 4.7, "ram_gb": 16, "speed": "⚡⚡", "quality": "⭐⭐⭐⭐",
        "description": "Meta's Llama 3, excellent for general tasks",
        "use_case": "General purpose, reasoning, conversation",
        "sha256": None,
    },
    "mistral-7b-q4": {
        "name": "Mistral 7B v0.3 (Q4)",
        "ollama": "mistral:7b",
        "hf_repo": "mistralai/Mistral-7B-Instruct-v0.3",
        "url": "https://huggingface.co/bartowski/Mistral-7B-Instruct-v0.3-GGUF/resolve/main/Mistral-7B-Instruct-v0.3-Q4_K_M.gguf",
        "filename": "mistral-7b-instruct-v0.3-q4.gguf",
        "size_gb": 4.4, "ram_gb": 16, "speed": "⚡⚡", "quality": "⭐⭐⭐⭐",
        "description": "Excellent for coding, reasoning, and analysis",
        "use_case": "Code generation, technical writing, reasoning",
        "sha256": None,
    },
}


class ModelManager:
    """Manages LLM models: discovery, download, installation"""

    def __init__(self, models_dir: Path):
        self.models_dir = Path(models_dir).expanduser()
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.catalog_path = self.models_dir / "catalog.json"
        self._load_catalog()

    def _load_catalog(self):
        """Load model catalog (built-in + custom)"""
        self.catalog = MODEL_CATALOG.copy()

        # Load custom models if catalog exists
        if self.catalog_path.exists():
            try:
                with open(self.catalog_path, 'r') as f:
                    custom = json.load(f)
                    self.catalog.update(custom)
            except Exception:
                pass  # Ignore errors, use built-in catalog

    def list_catalog(self) -> Dict:
        """List all models in catalog"""
        return self.catalog

    def ollama_tag(self, model_id: str) -> Optional[str]:
        """Ollama tag for a catalog id (None if unknown)."""
        info = self.catalog.get(model_id)
        return info.get("ollama") if info else None

    def hf_repo(self, model_id: str) -> Optional[str]:
        """HuggingFace repo for a catalog id (None if unknown)."""
        info = self.catalog.get(model_id)
        return info.get("hf_repo") if info else None

    def list_installed(self) -> List[Dict]:
        """List installed models (local GGUF + Ollama tags when reachable)."""
        installed = []

        for file in self.models_dir.glob("*.gguf"):
            size_bytes = file.stat().st_size
            size_gb = size_bytes / (1024 ** 3)

            # Try to match with catalog
            model_id = None
            for mid, info in self.catalog.items():
                if info["filename"] == file.name:
                    model_id = mid
                    break

            installed.append({
                "path": str(file),
                "filename": file.name,
                "size_gb": size_gb,
                "model_id": model_id,
                "backend": "llamacpp",
                "name": self.catalog[model_id]["name"] if model_id else file.stem,
            })

        # Add Ollama-pulled models (best-effort, skipped when Ollama is down)
        try:
            from .core.backends import ollama_is_available
            import httpx
            if ollama_is_available():
                r = httpx.get("http://localhost:11434/api/tags", timeout=3.0)
                for m in r.json().get("models", []):
                    name = m.get("name", "")
                    size_gb = m.get("size", 0) / (1024 ** 3)
                    model_id = next(
                        (mid for mid, info in self.catalog.items() if info.get("ollama") == name),
                        None,
                    )
                    installed.append({
                        "path": f"ollama:{name}",
                        "filename": name,
                        "size_gb": size_gb,
                        "model_id": model_id,
                        "backend": "ollama",
                        "name": self.catalog[model_id]["name"] if model_id else name,
                    })
        except Exception:
            pass

        return installed

    def pull_ollama(self, model_id: str, host: str = "http://localhost:11434") -> str:
        """Pull a model via Ollama (returns the tag). Streams progress to logs."""
        tag = self.ollama_tag(model_id)
        if not tag:
            # allow raw tags like qwen2.5:1.5b
            tag = model_id if ":" in model_id else None
        if not tag:
            raise ValueError(f"Model '{model_id}' not found in catalog and not a valid Ollama tag")
        import httpx
        with httpx.stream("POST", f"{host.rstrip('/')}/api/pull", json={"name": tag}, timeout=None) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if line and "error" in line.lower():
                    raise RuntimeError(f"Ollama pull failed: {line}")
        return tag

    def download(self, model_id: str, progress_callback=None) -> Path:
        """Download a GGUF model from the catalog"""
        if model_id not in self.catalog:
            raise ValueError(f"Model '{model_id}' not found in catalog")

        model_info = self.catalog[model_id]
        url = model_info.get("url")
        if not url:
            raise ValueError(
                f"Model '{model_id}' has no direct GGUF URL — use `ollama pull {model_info.get('ollama')}` "
                f"or download {model_info.get('hf_repo')} from HuggingFace"
            )
        filename = model_info["filename"]
        output_path = self.models_dir / filename

        # Check if already downloaded
        if output_path.exists():
            return output_path

        # Download with progress
        def _progress(block_num, block_size, total_size):
            if progress_callback and total_size > 0:
                downloaded = block_num * block_size
                percent = min(100, (downloaded / total_size) * 100)
                progress_callback(downloaded, total_size, percent)

        # Download to temp file first
        temp_path = output_path.with_suffix('.tmp')

        try:
            urllib.request.urlretrieve(url, temp_path, _progress)

            # Sanity-check size (warn, don't fail — repos update quants)
            size_bytes = temp_path.stat().st_size
            size_gb = size_bytes / (1024 ** 3)
            expected_gb = model_info["size_gb"]
            if size_gb < 0.05:
                raise ValueError(f"Downloaded file suspiciously small ({size_gb:.3f}GB) — download likely failed")
            if abs(size_gb - expected_gb) > (expected_gb * 0.25):
                logger.warning("Downloaded size %.2fGB differs from catalog %.2fGB", size_gb, expected_gb)

            # Verify checksum only when a real one is cataloged
            if model_info.get("sha256"):
                sha256 = hashlib.sha256()
                with open(temp_path, 'rb') as f:
                    for chunk in iter(lambda: f.read(1024 * 1024), b''):
                        sha256.update(chunk)

                if sha256.hexdigest() != model_info["sha256"]:
                    raise ValueError("Checksum verification failed")

            # Move to final location
            temp_path.rename(output_path)

            return output_path

        except Exception as e:
            # Clean up temp file on error
            if temp_path.exists():
                temp_path.unlink()
            raise e

    def remove(self, model_path: str) -> bool:
        """Remove an installed model"""
        if model_path.startswith("ollama:"):
            import httpx
            tag = model_path.split("ollama:", 1)[1]
            r = httpx.delete("http://localhost:11434/api/delete", json={"name": tag}, timeout=10.0)
            return r.status_code == 200
        path = Path(model_path).expanduser()

        if not path.exists():
            return False

        if not path.is_relative_to(self.models_dir):
            raise ValueError("Can only remove models from models directory")

        path.unlink()
        return True

    def get_model_info(self, model_id: str) -> Optional[Dict]:
        """Get detailed info about a model"""
        if model_id in self.catalog:
            info = self.catalog[model_id].copy()

            # Check if installed
            model_path = self.models_dir / info["filename"]
            info["installed"] = model_path.exists()

            if info["installed"]:
                info["path"] = str(model_path)
                size_bytes = model_path.stat().st_size
                info["actual_size_gb"] = size_bytes / (1024 ** 3)

            return info

        return None

    def recommend(self, available_ram_gb: float = 8.0, use_case: str = "") -> str:
        """Recommend a model based on system resources and use case"""
        use_case = (use_case or "").lower()
        if "code" in use_case:
            return "mistral-7b-q4" if available_ram_gb >= 16 else "qwen2.5-3b-q4"
        if "reason" in use_case:
            return "qwen3-4b" if available_ram_gb >= 8 else "qwen3-1.7b"
        if available_ram_gb < 4:
            return "qwen2.5-1.5b-q4"
        elif available_ram_gb < 8:
            return "smollm2-1.7b"
        elif available_ram_gb < 16:
            return "qwen2.5-3b-q4"
        else:
            return "qwen2.5-7b-q4"
