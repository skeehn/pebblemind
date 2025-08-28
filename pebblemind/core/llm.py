"""LLM Engine using llama.cpp with BLAS acceleration"""

import asyncio
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
import os

from llama_cpp import Llama
from ..config import LLMConfig

logger = logging.getLogger(__name__)


class LLMEngine:
    """LLM inference engine using llama.cpp with CPU optimizations"""

    def __init__(self, config: LLMConfig):
        """Initialize LLM engine with configuration"""
        self.config = config
        self.model: Optional[Llama] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the LLM model with optimized settings"""
        if self._initialized:
            return

        try:
            logger.info(f"Initializing LLM engine with model: {self.config.model_name}")

            # Set BLAS optimization environment variables
            if self.config.enable_blas:
                self._configure_blas()

            # Set thread optimization
            if self.config.threads == -1:
                # Auto-detect optimal thread count
                import multiprocessing
                self.config.threads = max(1, multiprocessing.cpu_count() // 2)

            # Model loading parameters
            model_params = {
                "model_path": self.config.model_path,
                "n_ctx": self.config.context_length,
                "n_threads": self.config.threads,
                "n_batch": self.config.batch_size,
                "verbose": False,  # Reduce logging noise
            }

            # Add BLAS-specific optimizations if enabled
            if self.config.enable_blas:
                model_params.update({
                    "blas_vendor": self.config.blas_vendor,
                    "use_mlock": True,  # Lock model in memory
                    "use_mmap": True,   # Memory map the model
                })

            # Add native optimizations if enabled
            if self.config.enable_native:
                model_params["use_native"] = True

            # Load the model (this may take a while)
            logger.info("Loading LLM model... This may take a few minutes.")
            self.model = Llama(**model_params)

            self._initialized = True
            logger.info("LLM engine initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize LLM engine: {e}")
            raise

    def _configure_blas(self) -> None:
        """Configure BLAS acceleration environment variables"""
        # Set optimal thread counts for BLAS operations
        if self.config.blas_vendor.lower() == "openblas":
            os.environ.setdefault("OPENBLAS_NUM_THREADS", str(self.config.threads))
            os.environ.setdefault("GOTO_NUM_THREADS", str(self.config.threads))

        elif self.config.blas_vendor.lower() == "mkl":
            os.environ.setdefault("MKL_NUM_THREADS", str(self.config.threads))
            os.environ.setdefault("MKL_DYNAMIC", "FALSE")

        elif self.config.blas_vendor.lower() == "blis":
            os.environ.setdefault("BLIS_NUM_THREADS", str(self.config.threads))

        # Set general threading environment
        os.environ.setdefault("OMP_NUM_THREADS", str(self.config.threads))
        os.environ.setdefault("NUMEXPR_NUM_THREADS", str(self.config.threads))

        logger.info(f"Configured {self.config.blas_vendor} with {self.config.threads} threads")

    async def generate(
        self,
        message: str,
        context: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate text response using the LLM"""
        if not self._initialized or not self.model:
            raise RuntimeError("LLM engine not initialized")

        try:
            # Build the conversation context
            messages = []

            # Add system prompt if provided
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            else:
                # Default system prompt
                messages.append({
                    "role": "system",
                    "content": "You are PebbleMind, a helpful and knowledgeable AI assistant. "
                              "You provide accurate, helpful responses while being concise and clear."
                })

            # Add context documents if provided
            if context:
                context_text = "\n\n".join(context)
                messages.append({
                    "role": "system",
                    "content": f"Relevant context information:\n{context_text}"
                })

            # Add user message
            messages.append({"role": "user", "content": message})

            # Generation parameters
            generation_params = {
                "messages": messages,
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                "temperature": kwargs.get("temperature", self.config.temperature),
                "top_p": kwargs.get("top_p", self.config.top_p),
                "top_k": kwargs.get("top_k", self.config.top_k),
                "stream": False,
            }

            # Run generation in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model.create_chat_completion(**generation_params)
            )

            # Extract the response text
            if "choices" in response and response["choices"]:
                return response["choices"][0]["message"]["content"]
            else:
                raise RuntimeError("No response generated")

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise

    async def generate_stream(
        self,
        message: str,
        context: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ):
        """Generate text response with streaming"""
        if not self._initialized or not self.model:
            raise RuntimeError("LLM engine not initialized")

        try:
            # Build conversation context (same as generate method)
            messages = []

            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            else:
                messages.append({
                    "role": "system",
                    "content": "You are PebbleMind, a helpful and knowledgeable AI assistant."
                })

            if context:
                context_text = "\n\n".join(context)
                messages.append({
                    "role": "system",
                    "content": f"Relevant context information:\n{context_text}"
                })

            messages.append({"role": "user", "content": message})

            # Enable streaming
            generation_params = {
                "messages": messages,
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                "temperature": kwargs.get("temperature", self.config.temperature),
                "top_p": kwargs.get("top_p", self.config.top_p),
                "top_k": kwargs.get("top_k", self.config.top_k),
                "stream": True,
            }

            # Stream the response
            loop = asyncio.get_event_loop()
            stream = await loop.run_in_executor(
                None,
                lambda: self.model.create_chat_completion(**generation_params)
            )

            for chunk in stream:
                if "choices" in chunk and chunk["choices"]:
                    delta = chunk["choices"][0].get("delta", {})
                    if "content" in delta:
                        yield delta["content"]

        except Exception as e:
            logger.error(f"Error in streaming generation: {e}")
            raise

    async def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model"""
        if not self._initialized or not self.model:
            return {"status": "not_initialized"}

        try:
            return {
                "status": "loaded",
                "model_name": self.config.model_name,
                "context_length": self.config.context_length,
                "threads": self.config.threads,
                "blas_enabled": self.config.enable_blas,
                "blas_vendor": self.config.blas_vendor if self.config.enable_blas else None,
                "model_path": self.config.model_path,
                "model_size": Path(self.config.model_path).stat().st_size if Path(self.config.model_path).exists() else None,
            }
        except Exception as e:
            logger.error(f"Error getting model info: {e}")
            return {"status": "error", "error": str(e)}

    async def cleanup(self) -> None:
        """Clean up resources"""
        if self.model:
            # llama.cpp handles cleanup automatically
            self.model = None

        self._initialized = False
        logger.info("LLM engine cleaned up")
