"""Efficient Reasoning Engine for PebbleMind - Optimized for Lightweight Devices like MacBook Air"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from llama_cpp import Llama

from .config import LLMConfig

logger = logging.getLogger(__name__)

# Model path mapping for different Qwen2.5 sizes optimized for efficiency
MODEL_PATHS = {
    "1.5b": "models/qwen2.5-1.5b-instruct-q4_k_m.gguf",
    "3b": "models/qwen2.5-3b-instruct-q4_k_m.gguf",
    "7b": "models/qwen2.5-7b-instruct-q4_k_m.gguf",
}

# Model names mapping
MODEL_NAMES = {
    "1.5b": "Qwen2.5-1.5B-Instruct-Q4K-Mini",
    "3b": "Qwen2.5-3B-Instruct-Q4K-Balanced",
    "7b": "Qwen2.5-7B-Instruct-Q4K-High",
}


class EfficientReasoningEngine:
    """Highly optimized reasoning engine designed for maximum efficiency on lightweight devices like MacBook Air"""

    def __init__(self, config: LLMConfig):
        """Initialize the efficient reasoning engine with configuration"""
        self.config = config
        self.model: Optional[Llama] = None
        self._initialized = False

        # MacBook Air optimization defaults
        self._mac_optimized_params = {
            "context_length": 2048,  # Reduced for memory efficiency
            "batch_size": 256,  # Reduced for memory efficiency
            "threads": 4,  # Conservative for older MacBooks
        }

        # Performance tracking
        self._performance_stats = {
            "total_tokens_processed": 0,
            "average_tokens_per_second": 0.0,
            "total_generation_time": 0.0,
            "total_context_switches": 0,
        }

    async def initialize(self, device_type: str = "macbook_air") -> None:
        """Initialize the reasoning engine with device-specific optimizations"""
        if self._initialized:
            return

        try:
            logger.info(
                "Initializing Efficient Reasoning Engine for lightweight devices..."
            )

            # Apply device-specific optimizations
            if device_type.lower() == "macbook_air":
                # MacBook Air specific optimizations
                self.config.context_length = self._mac_optimized_params[
                    "context_length"
                ]
                self.config.batch_size = self._mac_optimized_params["batch_size"]
                self.config.threads = self._mac_optimized_params["threads"]

                # Additional MacBook Air optimizations
                import os

                os.environ["OMP_NUM_THREADS"] = str(self.config.threads)
                os.environ["OPENBLAS_NUM_THREADS"] = str(self.config.threads)
                os.environ["VECLIB_MAXIMUM_THREADS"] = str(self.config.threads)
                os.environ["NUMEXPR_NUM_THREADS"] = str(self.config.threads)

            # Auto-detect optimal thread count if not specified
            if self.config.threads == -1 or self.config.threads > 8:
                import multiprocessing

                # Use fewer threads on lightweight devices to avoid overheating
                self.config.threads = min(6, max(2, multiprocessing.cpu_count() - 2))

            # Validate and resolve model path
            model_path = self._resolve_model_path()
            if not self._validate_model_path(model_path):
                raise RuntimeError(f"Invalid model path: {model_path}")

            logger.info(
                f"Loading optimized model: {self.config.model_name} ({self.config.model_size})"
            )

            # Optimize model loading parameters for efficiency
            model_params = {
                "model_path": model_path,
                "n_ctx": self.config.context_length,
                "n_threads": self.config.threads,
                "n_batch": self.config.batch_size,
                "n_gpu_layers": 0,  # CPU-only for consistent performance
                "use_mlock": False,  # Disable mlock to reduce memory pressure
                "use_mmap": True,  # Use memory mapping for efficiency
                "low_vram": True,  # Optimize for low VRAM (even though using CPU)
                "verbose": False,
            }

            # Load the model
            self.model = Llama(**model_params)
            self._initialized = True

            logger.info(
                f"Efficient Reasoning Engine initialized successfully on {device_type}"
            )
            logger.info(
                f"Model loaded with {self.config.threads} threads and {self.config.context_length} context length"
            )

        except Exception as e:
            logger.error(f"Failed to initialize Efficient Reasoning Engine: {e}")
            raise

    def _resolve_model_path(self) -> str:
        """Resolve the model path based on configuration with efficiency in mind"""
        if self.config.model_path:
            return self.config.model_path

        # For lightweight devices, prioritize 1.5B model as default
        if self.config.model_size not in MODEL_PATHS:
            logger.info("Model size not specified, defaulting to efficient 1.5B model")
            self.config.model_size = "1.5b"
            self.config.model_name = MODEL_NAMES["1.5b"]

        model_path = MODEL_PATHS[self.config.model_size]
        self.config.model_name = MODEL_NAMES[self.config.model_size]
        return model_path

    def _validate_model_path(self, model_path: str) -> bool:
        """Validate that the model file exists and is appropriate for lightweight use"""
        path = Path(model_path)
        if not path.exists():
            logger.error(f"Model file not found: {model_path}")
            return False

        if not path.is_file():
            logger.error(f"Model path is not a file: {model_path}")
            return False

        # Check file size (should be reasonable for lightweight performance)
        file_size = path.stat().st_size
        max_size_gb = 3.0  # Maximum recommended size for lightweight devices
        size_gb = file_size / (1024 * 1024 * 1024)

        if size_gb > max_size_gb:
            logger.warning(
                f"Model file is larger than recommended for lightweight devices: {size_gb:.2f} GB"
            )

        logger.info(f"Model file validated: {model_path} ({size_gb:.2f} GB)")
        return True

    async def generate(
        self,
        message: str,
        context: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Generate text with optimized performance for lightweight devices"""
        if not self._initialized or not self.model:
            raise RuntimeError("Efficient Reasoning Engine not initialized")

        start_time = time.time()

        try:
            # Build the conversation context with efficiency in mind
            messages = []

            # Add system prompt with lightweight instructions
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            else:
                # Minimal but effective system prompt for reasoning
                messages.append(
                    {
                        "role": "system",
                        "content": (
                            "You are PebbleMind, a highly efficient AI assistant running on lightweight hardware. "
                            "Provide concise, accurate responses with clear reasoning. "
                            "Focus on being helpful while maintaining efficiency."
                        ),
                    }
                )

            # Add context if provided (but limit to maintain efficiency)
            if context:
                # Take only the most recent context items to maintain efficiency
                recent_context = context[-3:] if len(context) > 3 else context
                for ctx in recent_context:
                    messages.append({"role": "system", "content": f"Context: {ctx}"})

            # Add user message
            messages.append({"role": "user", "content": message})

            # Use passed parameters or defaults with efficiency in mind
            generation_params = {
                "messages": messages,
                "max_tokens": max_tokens
                or min(256, self.config.max_tokens),  # Reduced for efficiency
                "temperature": temperature
                or min(0.7, self.config.temperature),  # Conservative for quality
                "top_p": 0.9,  # Standard value for good quality
                "top_k": 40,  # Conservative for efficiency
                "stream": False,
                "stop": ["\n\n"],  # Stop early to maintain efficiency
            }

            # Run generation in thread pool with efficiency optimizations
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, lambda: self.model.create_chat_completion(**generation_params)
            )

            end_time = time.time()
            generation_time = end_time - start_time

            # Update performance stats
            if "choices" in response and response["choices"]:
                response_text = response["choices"][0]["message"]["content"]
                tokens_generated = len(response_text.split())

                self._performance_stats["total_tokens_processed"] += tokens_generated
                self._performance_stats["total_generation_time"] += generation_time
                self._performance_stats["total_context_switches"] += 1

                # Calculate average tokens per second
                if self._performance_stats["total_generation_time"] > 0:
                    self._performance_stats["average_tokens_per_second"] = (
                        self._performance_stats["total_tokens_processed"]
                        / self._performance_stats["total_generation_time"]
                    )

                return {
                    "response": response_text,
                    "generation_time": generation_time,
                    "tokens_generated": tokens_generated,
                    "tokens_per_second": (
                        tokens_generated / generation_time if generation_time > 0 else 0
                    ),
                    "model_info": {
                        "model_name": self.config.model_name,
                        "model_size": self.config.model_size,
                        "context_length": self.config.context_length,
                    },
                }
            else:
                raise RuntimeError("No response generated")

        except Exception as e:
            logger.error(f"Error in efficient generation: {e}")
            raise

    async def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for the reasoning engine"""
        return {
            "total_tokens_processed": self._performance_stats["total_tokens_processed"],
            "average_tokens_per_second": self._performance_stats[
                "average_tokens_per_second"
            ],
            "total_generation_time": self._performance_stats["total_generation_time"],
            "total_context_switches": self._performance_stats["total_context_switches"],
            "model_info": {
                "model_name": self.config.model_name,
                "model_size": self.config.model_size,
                "context_length": self.config.context_length,
                "threads": self.config.threads,
            },
        }

    async def cleanup(self) -> None:
        """Clean up resources efficiently"""
        if self.model:
            # Clear model from memory
            self.model = None

        self._initialized = False
        logger.info("Efficient Reasoning Engine cleaned up")
