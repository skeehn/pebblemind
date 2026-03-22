"""Configuration management for PebbleMind"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    """Configuration for LLM inference optimized for lightweight devices"""
    model_path: str = Field(default="", description="Path to the LLM model file (auto-detected if empty)")
    model_name: str = Field(default="Qwen2.5-1.5B-Instruct", description="Model name")
    model_size: str = Field(default="1.5b", description="Model size: 1.5b (ultra-light, MacBook Air optimized), 3b (balanced), 7b (high-quality)")
    context_length: int = Field(default=2048, description="Maximum context length (optimized for lightweight devices)")
    max_tokens: int = Field(default=256, description="Maximum tokens to generate (conservative for efficiency)")
    temperature: float = Field(default=0.7, description="Sampling temperature")
    top_p: float = Field(default=0.9, description="Top-p sampling parameter")
    top_k: int = Field(default=40, description="Top-k sampling parameter")
    threads: int = Field(default=-1, description="Number of threads (-1 for auto, conservative for lightweight devices)")
    batch_size: int = Field(default=256, description="Batch size for processing (reduced for memory efficiency)")
    enable_blas: bool = Field(default=True, description="Enable BLAS acceleration")
    blas_vendor: str = Field(default="OpenBLAS", description="BLAS vendor to use")
    enable_native: bool = Field(default=True, description="Enable native optimizations")
    enable_gpu_offload: bool = Field(default=False, description="Enable GPU layer offloading (CPU-only by default for consistency)")
    gpu_layers: int = Field(default=0, description="Number of layers to offload to GPU (-1 for auto)")
    auto_detect_gpu: bool = Field(default=True, description="Automatically detect and configure GPU")


class VoiceConfig(BaseModel):
    """Configuration for voice processing"""
    stt_model: str = Field(default="base.en", description="Whisper model for speech-to-text")
    stt_threads: int = Field(default=4, description="Threads for STT processing")
    tts_model: str = Field(default="amy-low", description="Piper TTS voice model")
    tts_threads: int = Field(default=4, description="Threads for TTS processing")
    sample_rate: int = Field(default=22050, description="Audio sample rate")
    channels: int = Field(default=1, description="Audio channels")


class RAGConfig(BaseModel):
    """Configuration for RAG system optimized for lightweight devices"""
    embedding_model: str = Field(default="BAAI/bge-small-en-v1.5", description="Lightweight embedding model")
    embedding_dim: int = Field(default=384, description="Embedding dimension")
    vector_db_path: str = Field(default="./data/vectors.db", description="Vector database path")
    chunk_size: int = Field(default=512, description="Document chunk size")
    chunk_overlap: int = Field(default=32, description="Overlap between chunks (reduced for efficiency)")
    max_results: int = Field(default=3, description="Maximum search results (reduced for efficiency)")
    similarity_threshold: float = Field(default=0.7, description="Similarity threshold")


class APIConfig(BaseModel):
    """Configuration for API server"""
    host: str = Field(default="localhost", description="API server host")
    port: int = Field(default=8000, description="API server port")
    cors_origins: list = Field(default=["*"], description="CORS allowed origins")
    api_key: Optional[str] = Field(default=None, description="API key for authentication")

    # HTTPS/SSL Configuration
    enable_https: bool = Field(default=False, description="Enable HTTPS/SSL")
    ssl_cert_path: Optional[str] = Field(default=None, description="Path to SSL certificate file")
    ssl_key_path: Optional[str] = Field(default=None, description="Path to SSL private key file")
    ssl_ca_certs: Optional[str] = Field(default=None, description="Path to CA certificates file")

    # Security headers
    enable_security_headers: bool = Field(default=True, description="Enable security headers")


class DesktopConfig(BaseModel):
    """Configuration for desktop application"""
    window_width: int = Field(default=1200, description="Window width")
    window_height: int = Field(default=800, description="Window height")
    enable_tray: bool = Field(default=True, description="Enable system tray")
    start_minimized: bool = Field(default=False, description="Start minimized")


class Config(BaseModel):
    """Main configuration class"""
    llm: LLMConfig = Field(default_factory=LLMConfig)
    voice: VoiceConfig = Field(default_factory=VoiceConfig)
    rag: RAGConfig = Field(default_factory=RAGConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    desktop: DesktopConfig = Field(default_factory=DesktopConfig)

    data_dir: str = Field(default="./data", description="Data directory")
    cache_dir: str = Field(default="./cache", description="Cache directory")
    log_level: str = Field(default="INFO", description="Logging level")

    @classmethod
    def from_file(cls, config_path: str) -> "Config":
        """Load configuration from YAML file"""
        config_path = Path(config_path)
        if not config_path.exists():
            return cls()

        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)

        return cls(**(data or {}))

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables"""
        # This would parse environment variables with PEBBLEMIND_ prefix
        return cls()

    def to_file(self, config_path: str) -> None:
        """Save configuration to YAML file"""
        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, 'w') as f:
            yaml.dump(self.model_dump(), f, default_flow_style=False)

    @property
    def data_path(self) -> Path:
        """Get data directory path"""
        return Path(self.data_dir).expanduser().resolve()

    @property
    def cache_path(self) -> Path:
        """Get cache directory path"""
        return Path(self.cache_dir).expanduser().resolve()


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance"""
    global _config
    if _config is None:
        _config = Config()
    return _config


def set_config(config: Config) -> None:
    """Set the global configuration instance"""
    global _config
    _config = config


def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from file or create default"""
    if config_path and Path(config_path).exists():
        config = Config.from_file(config_path)
    else:
        config = Config()

    set_config(config)
    return config
