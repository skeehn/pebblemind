#!/usr/bin/env python3
"""
Model Download Script for PebbleMind

Downloads required models from HuggingFace:
- Qwen2.5 LLM models (1.5B, 3B, 7B)
- BGE-small embedding model
- Optional: whisper and Piper voice models
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional
import hashlib

try:
    from huggingface_hub import hf_hub_download, snapshot_download
    from tqdm import tqdm
except ImportError:
    print("Error: Required packages not installed.")
    print("Please install: pip install huggingface_hub tqdm")
    sys.exit(1)


# Model repository configurations
MODELS = {
    "llm": {
        "1.5b": {
            "repo_id": "Qwen/Qwen2.5-1.5B-Instruct-GGUF",
            "filename": "qwen2.5-1.5b-instruct-q4_k_m.gguf",
            "size_mb": 950,
            "description": "Ultra-light 1.5B model (optimized for MacBook Air)"
        },
        "3b": {
            "repo_id": "Qwen/Qwen2.5-3B-Instruct-GGUF",
            "filename": "qwen2.5-3b-instruct-q4_k_m.gguf",
            "size_mb": 1900,
            "description": "Balanced 3B model (recommended default)"
        },
        "7b": {
            "repo_id": "Qwen/Qwen2.5-7B-Instruct-GGUF",
            "filename": "qwen2.5-7b-instruct-q4_k_m.gguf",
            "size_mb": 4300,
            "description": "High-quality 7B model (best performance)"
        }
    },
    "embedding": {
        "repo_id": "BAAI/bge-small-en-v1.5",
        "description": "Lightweight embedding model for RAG (384 dimensions)"
    }
}

# MD5 checksums for verification (optional - can be added)
CHECKSUMS = {
    # Add checksums here for verification
}


class ModelDownloader:
    """Manages model downloads from HuggingFace"""

    def __init__(self, models_dir: str = "models", cache_dir: Optional[str] = None):
        """
        Initialize model downloader

        Args:
            models_dir: Directory to store downloaded models
            cache_dir: HuggingFace cache directory (optional)
        """
        self.models_dir = Path(models_dir)
        self.cache_dir = cache_dir
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def download_llm_model(self, size: str) -> Path:
        """
        Download a Qwen2.5 LLM model

        Args:
            size: Model size ("1.5b", "3b", or "7b")

        Returns:
            Path to downloaded model file
        """
        if size not in MODELS["llm"]:
            raise ValueError(f"Invalid model size: {size}. Choose from: {list(MODELS['llm'].keys())}")

        model_info = MODELS["llm"][size]
        print(f"\n📦 Downloading {size.upper()} LLM Model")
        print(f"   Description: {model_info['description']}")
        print(f"   Size: ~{model_info['size_mb']} MB")
        print(f"   Repo: {model_info['repo_id']}")

        # Check if already downloaded
        model_path = self.models_dir / model_info["filename"]
        if model_path.exists():
            print(f"   ✓ Model already exists at: {model_path}")
            return model_path

        try:
            # Download with progress bar
            print(f"   Downloading {model_info['filename']}...")

            downloaded_path = hf_hub_download(
                repo_id=model_info["repo_id"],
                filename=model_info["filename"],
                local_dir=str(self.models_dir),
                cache_dir=self.cache_dir,
                resume_download=True
            )

            print(f"   ✓ Downloaded successfully to: {downloaded_path}")
            return Path(downloaded_path)

        except Exception as e:
            print(f"   ✗ Download failed: {e}")
            raise

    def download_embedding_model(self) -> Path:
        """
        Download BGE-small embedding model

        Returns:
            Path to downloaded model directory
        """
        model_info = MODELS["embedding"]
        print(f"\n📦 Downloading Embedding Model")
        print(f"   Description: {model_info['description']}")
        print(f"   Repo: {model_info['repo_id']}")

        model_path = self.models_dir / "bge-small-en-v1.5"

        # Check if already downloaded
        if model_path.exists() and list(model_path.glob("*.bin")):
            print(f"   ✓ Model already exists at: {model_path}")
            return model_path

        try:
            print(f"   Downloading embedding model...")

            # Download entire repository
            snapshot_download(
                repo_id=model_info["repo_id"],
                local_dir=str(model_path),
                cache_dir=self.cache_dir,
                resume_download=True
            )

            print(f"   ✓ Downloaded successfully to: {model_path}")
            return model_path

        except Exception as e:
            print(f"   ✗ Download failed: {e}")
            raise

    def download_all_llm_models(self) -> dict[str, Path]:
        """Download all LLM models"""
        models = {}
        for size in MODELS["llm"].keys():
            try:
                models[size] = self.download_llm_model(size)
            except Exception as e:
                print(f"   Warning: Failed to download {size} model: {e}")
        return models

    def verify_checksum(self, file_path: Path, expected_checksum: str) -> bool:
        """
        Verify file checksum

        Args:
            file_path: Path to file
            expected_checksum: Expected MD5 checksum

        Returns:
            True if checksum matches
        """
        print(f"   Verifying checksum for {file_path.name}...")
        md5 = hashlib.md5()

        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                md5.update(chunk)

        actual_checksum = md5.hexdigest()
        matches = actual_checksum == expected_checksum

        if matches:
            print(f"   ✓ Checksum verified")
        else:
            print(f"   ✗ Checksum mismatch!")
            print(f"     Expected: {expected_checksum}")
            print(f"     Got:      {actual_checksum}")

        return matches

    def get_model_info(self) -> dict:
        """Get information about all available models"""
        return MODELS

    def list_downloaded_models(self) -> dict:
        """List all downloaded models"""
        downloaded = {
            "llm": {},
            "embedding": None
        }

        # Check LLM models
        for size, info in MODELS["llm"].items():
            model_path = self.models_dir / info["filename"]
            if model_path.exists():
                downloaded["llm"][size] = {
                    "path": str(model_path),
                    "size_mb": model_path.stat().st_size / (1024 * 1024)
                }

        # Check embedding model
        embedding_path = self.models_dir / "bge-small-en-v1.5"
        if embedding_path.exists():
            downloaded["embedding"] = {
                "path": str(embedding_path),
                "size_mb": sum(f.stat().st_size for f in embedding_path.rglob('*') if f.is_file()) / (1024 * 1024)
            }

        return downloaded


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Download PebbleMind models from HuggingFace",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download the recommended 3B model
  python download_models.py --llm 3b

  # Download all LLM models
  python download_models.py --llm all

  # Download embedding model only
  python download_models.py --embedding

  # Download everything
  python download_models.py --all

  # List downloaded models
  python download_models.py --list

  # Use custom directory
  python download_models.py --llm 3b --models-dir /path/to/models
        """
    )

    parser.add_argument(
        "--llm",
        type=str,
        choices=["1.5b", "3b", "7b", "all"],
        help="Download LLM model (1.5b, 3b, 7b, or all)"
    )

    parser.add_argument(
        "--embedding",
        action="store_true",
        help="Download embedding model"
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Download all models"
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List downloaded models"
    )

    parser.add_argument(
        "--models-dir",
        type=str,
        default="models",
        help="Directory to store models (default: models/)"
    )

    parser.add_argument(
        "--cache-dir",
        type=str,
        default=None,
        help="HuggingFace cache directory (optional)"
    )

    args = parser.parse_args()

    # Initialize downloader
    downloader = ModelDownloader(
        models_dir=args.models_dir,
        cache_dir=args.cache_dir
    )

    # List mode
    if args.list:
        print("\n📋 Downloaded Models:")
        downloaded = downloader.list_downloaded_models()

        if downloaded["llm"]:
            print("\n  LLM Models:")
            for size, info in downloaded["llm"].items():
                print(f"    ✓ {size}: {info['path']} ({info['size_mb']:.1f} MB)")
        else:
            print("    No LLM models downloaded")

        if downloaded["embedding"]:
            print("\n  Embedding Model:")
            print(f"    ✓ BGE-small: {downloaded['embedding']['path']} ({downloaded['embedding']['size_mb']:.1f} MB)")
        else:
            print("    No embedding model downloaded")

        return

    # Download mode
    if not (args.llm or args.embedding or args.all):
        parser.print_help()
        return

    print("="*60)
    print("  PebbleMind Model Downloader")
    print("="*60)

    try:
        # Download all models
        if args.all:
            print("\n🚀 Downloading all models...")
            downloader.download_all_llm_models()
            downloader.download_embedding_model()

        # Download LLM model
        elif args.llm:
            if args.llm == "all":
                downloader.download_all_llm_models()
            else:
                downloader.download_llm_model(args.llm)

        # Download embedding model
        if args.embedding or args.all:
            downloader.download_embedding_model()

        print("\n" + "="*60)
        print("  ✓ Download Complete!")
        print("="*60)
        print(f"\nModels saved to: {Path(args.models_dir).absolute()}")
        print("\nNext steps:")
        print("  1. Update pebblemind.yaml with model paths")
        print("  2. Run: pebblemind chat --interactive")

    except KeyboardInterrupt:
        print("\n\n⚠ Download cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
