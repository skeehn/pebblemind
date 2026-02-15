"""PebbleMind: CPU-First Local AI Assistant

A privacy-first, CPU-optimized AI assistant that runs entirely on your local machine.
No cloud dependencies, no GPU requirements, just powerful local AI capabilities.

Features:
- Local LLM inference with llama.cpp and BLAS acceleration
- Voice input/output with whisper.cpp and Piper TTS
- RAG system with vector search and document indexing
- OpenAI-compatible API for easy integration
- Cross-platform desktop application with Tauri
- World's smallest intelligent reasoning model optimized for MacBook Air and similar devices

"""

__version__ = "0.1.0"
__author__ = "PebbleMind Team"
__email__ = "team@pebblemind.ai"

from .config import Config

# Lazy import to avoid loading heavy dependencies at module import time
def __getattr__(name):
    if name == "PebbleMind":
        from .pebblemind_app import PebbleMind
        return PebbleMind
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ["Config", "PebbleMind"]
