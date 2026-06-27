"""
Model Management for PebbleMind

Handles model discovery, downloading, and management.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
import urllib.request
import hashlib


# Model catalog with recommended models
MODEL_CATALOG = {
    "qwen2.5-1.5b-q4": {
        "name": "Qwen 2.5 1.5B (Q4)",
        "size_gb": 1.0,
        "url": "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf",
        "filename": "qwen2.5-1.5b-instruct-q4_k_m.gguf",
        "speed": "⚡⚡⚡",
        "quality": "⭐⭐",
        "description": "Fast, lightweight model for quick responses and testing",
        "use_case": "Quick responses, testing, low-resource systems",
        "sha256": None,  # Optional: add checksum for verification
    },
    "qwen2.5-7b-q4": {
        "name": "Qwen 2.5 7B (Q4)",
        "size_gb": 4.4,
        "url": "https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_k_m.gguf",
        "filename": "qwen2.5-7b-instruct-q4_k_m.gguf",
        "speed": "⚡⚡",
        "quality": "⭐⭐⭐⭐",
        "description": "Balanced performance and quality, recommended default",
        "use_case": "General purpose, good balance of speed and quality",
        "sha256": None,
    },
    "llama-3-8b-q4": {
        "name": "Llama 3 8B (Q4)",
        "size_gb": 4.7,
        "url": "https://huggingface.co/QuantFactory/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf",
        "filename": "llama-3-8b-instruct-q4.gguf",
        "speed": "⚡⚡",
        "quality": "⭐⭐⭐⭐",
        "description": "Meta's Llama 3, excellent for general tasks",
        "use_case": "General purpose, reasoning, conversation",
        "sha256": None,
    },
    "mistral-7b-q4": {
        "name": "Mistral 7B v0.3 (Q4)",
        "size_gb": 4.4,
        "url": "https://huggingface.co/MaziyarPanahi/Mistral-7B-Instruct-v0.3-GGUF/resolve/main/Mistral-7B-Instruct-v0.3.Q4_K_M.gguf",
        "filename": "mistral-7b-instruct-v0.3-q4.gguf",
        "speed": "⚡⚡",
        "quality": "⭐⭐⭐⭐",
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
    
    def list_installed(self) -> List[Dict]:
        """List installed models"""
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
                "name": self.catalog[model_id]["name"] if model_id else file.stem,
            })
        
        return installed
    
    def download(self, model_id: str, progress_callback=None) -> Path:
        """Download a model from the catalog"""
        if model_id not in self.catalog:
            raise ValueError(f"Model '{model_id}' not found in catalog")
        
        model_info = self.catalog[model_id]
        url = model_info["url"]
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
            
            # Verify size
            size_bytes = temp_path.stat().st_size
            size_gb = size_bytes / (1024 ** 3)
            expected_gb = model_info["size_gb"]
            
            # Allow 10% variance in size (compression, metadata)
            if abs(size_gb - expected_gb) > (expected_gb * 0.1):
                raise ValueError(
                    f"Downloaded size ({size_gb:.2f}GB) doesn't match "
                    f"expected size ({expected_gb:.2f}GB)"
                )
            
            # Verify checksum if provided
            if model_info.get("sha256"):
                sha256 = hashlib.sha256()
                with open(temp_path, 'rb') as f:
                    for chunk in iter(lambda: f.read(4096), b''):
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
    
    def recommend(self, available_ram_gb: float = None, use_case: str = None) -> str:
        """Recommend a model based on system resources and use case"""
        # Simple heuristic: recommend based on available RAM
        if available_ram_gb:
            if available_ram_gb < 6:
                return "qwen2.5-1.5b-q4"  # Small model
            elif available_ram_gb < 16:
                return "qwen2.5-7b-q4"  # Medium model
            else:
                # Could recommend larger models if added to catalog
                return "qwen2.5-7b-q4"
        
        # Recommend based on use case
        if use_case:
            use_case = use_case.lower()
            if "code" in use_case or "programming" in use_case:
                return "mistral-7b-q4"
            elif "fast" in use_case or "quick" in use_case:
                return "qwen2.5-1.5b-q4"
        
        # Default recommendation
        return "qwen2.5-7b-q4"
