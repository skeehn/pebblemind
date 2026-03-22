"""LLM Engine using llama.cpp with BLAS acceleration - Optimized for Lightweight Devices"""

import asyncio
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
import os
import platform

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

from ..config import LLMConfig

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = (
    "You are PebbleMind, a highly efficient AI assistant running on lightweight hardware. "
    "Provide concise, accurate responses with clear reasoning. "
    "Focus on being helpful while maintaining efficiency."
)

# Model path mapping for different Qwen2.5 sizes
MODEL_PATHS = {
    "1.5b": "models/qwen2.5-1.5b-instruct-q4_k_m.gguf",
    "3b": "models/qwen2.5-3b-instruct-q4_k_m.gguf", 
    "7b": "models/qwen2.5-7b-instruct-q4_k_m.gguf"
}

# Model names mapping
MODEL_NAMES = {
    "1.5b": "Qwen2.5-1.5B-Instruct",
    "3b": "Qwen2.5-3B-Instruct",
    "7b": "Qwen2.5-7B-Instruct"
}


class LLMEngine:
    """LLM inference engine using llama.cpp with CPU optimizations"""

    def __init__(self, config: LLMConfig):
        """Initialize LLM engine with configuration"""
        self.config = config
        self.model: Optional[Llama] = None
        self._initialized = False
        self._gpu_available = False
        self._gpu_layers_available = 0

    def _detect_gpu_availability(self) -> bool:
        """Detect if GPU is available for offloading"""
        try:
            # Try to import CUDA libraries
            import ctypes
            import ctypes.util
            
            # Check for CUDA
            cuda_lib = ctypes.util.find_library("cuda")
            if cuda_lib:
                logger.info("CUDA library found")
                return True
                
            # Check for OpenCL
            opencl_lib = ctypes.util.find_library("OpenCL")
            if opencl_lib:
                logger.info("OpenCL library found")
                return True
                
            # Check for Metal (macOS)
            if platform.system() == "Darwin":
                metal_lib = ctypes.util.find_library("Metal")
                if metal_lib:
                    logger.info("Metal library found")
                    return True
                    
        except Exception as e:
            logger.debug(f"GPU detection failed: {e}")
            
        return False

    def _resolve_model_path(self) -> str:
        """Resolve the model path based on configuration"""
        # If model_path is explicitly set, use it
        if self.config.model_path:
            return self.config.model_path
            
        # Otherwise, use model_size to determine path
        if self.config.model_size in MODEL_PATHS:
            model_path = MODEL_PATHS[self.config.model_size]
            # Update model_name to match
            self.config.model_name = MODEL_NAMES[self.config.model_size]
            return model_path
            
        # Fallback to 3B model
        logger.warning(f"Unknown model size '{self.config.model_size}', defaulting to 3B")
        self.config.model_size = "3b"
        self.config.model_name = MODEL_NAMES["3b"]
        return MODEL_PATHS["3b"]

    def _validate_model_path(self, model_path: str) -> bool:
        """Validate that the model file exists and is accessible"""
        path = Path(model_path)
        if not path.exists():
            logger.error(f"Model file not found: {model_path}")
            return False
            
        if not path.is_file():
            logger.error(f"Model path is not a file: {model_path}")
            return False
            
        # Check file size (should be reasonable for a GGUF model)
        file_size = path.stat().st_size
        if file_size < 1024 * 1024:  # Less than 1MB is suspicious
            logger.warning(f"Model file seems too small: {file_size} bytes")
            
        logger.info(f"Model file validated: {model_path} ({file_size / (1024*1024*1024):.2f} GB)")
        return True

    async def initialize(self) -> None:
        """Initialize the LLM model with optimized settings for lightweight devices like MacBook Air"""
        if self._initialized:
            return

        if Llama is None:
            raise ImportError("llama-cpp-python not installed. Install with: pip install llama-cpp-python")

        try:
            # Resolve and validate model path
            model_path = self._resolve_model_path()
            if not self._validate_model_path(model_path):
                raise RuntimeError(f"Invalid model path: {model_path}")

            logger.info(f"Initializing LLM engine with model: {self.config.model_name} ({self.config.model_size})")

            # Set conservative parameters for lightweight devices
            if self.config.threads == -1 or self.config.threads > 6:
                # Use fewer threads for lightweight devices to avoid overheating
                import multiprocessing
                self.config.threads = min(6, max(2, multiprocessing.cpu_count() - 2))
                
            if self.config.context_length > 2048:
                # Reduce context length for better memory efficiency on lightweight devices
                self.config.context_length = min(self.config.context_length, 2048)

            # Set BLAS optimization environment variables
            if self.config.enable_blas:
                self._configure_blas()

            # Model loading parameters - optimized for lightweight devices
            model_params = {
                "model_path": model_path,
                "n_ctx": self.config.context_length,
                "n_threads": self.config.threads,
                "n_batch": self.config.batch_size,
                "verbose": False,  # Reduce logging noise
                "n_gpu_layers": 0,  # CPU-only by default for consistent performance on all devices
                "use_mlock": False,  # Disable mlock to reduce memory pressure on lightweight devices
                "use_mmap": True,    # Use memory mapping for efficiency
                "low_vram": True,    # Optimize for low VRAM (even though using CPU)
            }

            # Add BLAS-specific optimizations if enabled
            if self.config.enable_blas:
                model_params.update({
                    "blas_vendor": self.config.blas_vendor,
                })

            # Add native optimizations if enabled
            if self.config.enable_native:
                model_params["use_native"] = True

            # Only enable GPU offloading if explicitly requested and available
            # For lightweight devices, CPU-only is often more predictable
            if self.config.enable_gpu_offload:
                if self.config.auto_detect_gpu:
                    self._gpu_available = self._detect_gpu_availability()
                    logger.info(f"GPU detection: {'Available' if self._gpu_available else 'Not available'}")
                
                if self._gpu_available:
                    if self.config.gpu_layers == -1:
                        # Conservative GPU offloading for balanced performance
                        if self.config.model_size == "1.5b":
                            self.config.gpu_layers = 8
                        elif self.config.model_size == "3b":
                            self.config.gpu_layers = 16
                        elif self.config.model_size == "7b":
                            self.config.gpu_layers = 24  # Only for larger models where it makes sense
                        else:
                            self.config.gpu_layers = 16
                    
                    model_params["n_gpu_layers"] = self.config.gpu_layers
                    logger.info(f"GPU offloading enabled: {self.config.gpu_layers} layers")
                else:
                    model_params["n_gpu_layers"] = 0
                    logger.info("GPU not available, using CPU-only mode")
            else:
                model_params["n_gpu_layers"] = 0
                logger.info("Using CPU-only mode for consistent performance")

            # Load the model (this may take a while)
            logger.info("Loading LLM model with optimizations for lightweight devices...")
            self.model = Llama(**model_params)

            self._initialized = True
            logger.info("LLM engine initialized successfully with optimizations for lightweight devices")

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
        """Generate text response using the LLM with optimizations for lightweight devices"""
        if not self._initialized or not self.model:
            raise RuntimeError("LLM engine not initialized")

        try:
            messages = self._build_messages(message, context=context, system_prompt=system_prompt)
            generation_params = self._build_generation_params(messages, stream=False, **kwargs)

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
        stop_event: Optional[asyncio.Event] = None,
        **kwargs
    ):
        """Generate text response with streaming"""
        if not self._initialized or not self.model:
            raise RuntimeError("LLM engine not initialized")

        try:
            messages = self._build_messages(message, context=context, system_prompt=system_prompt)
            generation_params = self._build_generation_params(messages, stream=True, **kwargs)

            # Stream the response
            loop = asyncio.get_event_loop()
            stream = await loop.run_in_executor(
                None,
                lambda: self.model.create_chat_completion(**generation_params)
            )

            for chunk in stream:
                # Allow external cancellation
                if stop_event and stop_event.is_set():
                    break
                if "choices" in chunk and chunk["choices"]:
                    delta = chunk["choices"][0].get("delta", {})
                    if "content" in delta:
                        yield delta["content"]
                # Yield control to event loop for backpressure
                await asyncio.sleep(0)

        except Exception as e:
            logger.error(f"Error in streaming generation: {e}")
            raise

    def _build_messages(
        self,
        message: str,
        context: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """Build conversation messages consistently for regular and streaming generation."""
        messages: List[Dict[str, str]] = []

        messages.append({
            "role": "system",
            "content": system_prompt or DEFAULT_SYSTEM_PROMPT,
        })

        if context:
            recent_context = context[-3:] if len(context) > 3 else context
            for ctx in recent_context:
                messages.append({"role": "system", "content": f"Context: {ctx}"})

        messages.append({"role": "user", "content": message})
        return messages

    def _build_generation_params(
        self,
        messages: List[Dict[str, str]],
        *,
        stream: bool,
        **kwargs,
    ) -> Dict[str, Any]:
        """Build bounded generation parameters consistently for regular and streaming generation."""
        return {
            "messages": messages,
            "max_tokens": min(kwargs.get("max_tokens", self.config.max_tokens), 256),
            "temperature": min(kwargs.get("temperature", self.config.temperature), 0.7),
            "top_p": min(kwargs.get("top_p", self.config.top_p), 0.9),
            "top_k": kwargs.get("top_k", self.config.top_k),
            "stream": stream,
            "stop": ["\n\n"],
        }

    async def switch_model(self, model_size: str) -> bool:
        """Switch to a different model size without restarting the application"""
        if model_size not in MODEL_PATHS:
            logger.error(f"Invalid model size: {model_size}. Available: {list(MODEL_PATHS.keys())}")
            return False
            
        if model_size == self.config.model_size:
            logger.info(f"Already using model size: {model_size}")
            return True
            
        try:
            logger.info(f"Switching from {self.config.model_size} to {model_size} model")
            
            # Clean up current model
            if self.model:
                self.model = None
                
            # Update configuration
            self.config.model_size = model_size
            self.config.model_name = MODEL_NAMES[model_size]
            self.config.model_path = MODEL_PATHS[model_size]
            
            # Reinitialize with new model
            self._initialized = False
            await self.initialize()
            
            logger.info(f"Successfully switched to {model_size} model")
            return True
            
        except Exception as e:
            logger.error(f"Failed to switch model: {e}")
            return False

    async def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model"""
        if not self._initialized or not self.model:
            return {"status": "not_initialized"}

        try:
            model_path = self._resolve_model_path()
            file_size = Path(model_path).stat().st_size if Path(model_path).exists() else None
            
            return {
                "status": "loaded",
                "model_name": self.config.model_name,
                "model_size": self.config.model_size,
                "context_length": self.config.context_length,
                "threads": self.config.threads,
                "blas_enabled": self.config.enable_blas,
                "blas_vendor": self.config.blas_vendor if self.config.enable_blas else None,
                "model_path": model_path,
                "file_size_bytes": file_size,
                "file_size_gb": file_size / (1024*1024*1024) if file_size else None,
                "gpu_available": self._gpu_available,
                "gpu_offload_enabled": self.config.enable_gpu_offload and self._gpu_available,
                "gpu_layers": self.config.gpu_layers if self.config.enable_gpu_offload else 0,
                "available_models": list(MODEL_PATHS.keys()),
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
