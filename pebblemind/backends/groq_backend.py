"""
Groq API Integration for PebbleMind

Provides cloud-based LLM inference as an alternative to local llama.cpp.
Uses Groq's ultra-fast inference API.
"""

import asyncio
import logging
import os
from typing import Any, AsyncIterator, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class GroqLLMBackend:
    """Groq API backend for LLM inference"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "llama-3.1-70b-versatile",
        base_url: str = "https://api.groq.com/openai/v1",
    ):
        """
        Initialize Groq LLM backend

        Args:
            api_key: Groq API key (or set GROQ_API_KEY env var)
            model: Model to use (default: llama-3.1-70b-versatile)
            base_url: Groq API base URL
        """
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Groq API key required. Set GROQ_API_KEY environment variable "
                "or pass api_key parameter"
            )

        self.model = model
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

        logger.info(f"Initialized Groq backend with model: {model}")

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 256,
        temperature: float = 0.7,
        top_p: float = 0.9,
        **kwargs,
    ) -> str:
        """
        Generate text using Groq API

        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Top-p sampling
            **kwargs: Additional parameters

        Returns:
            Generated text
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": top_p,
                    "stream": False,
                },
            )
            response.raise_for_status()
            data = response.json()

            return data["choices"][0]["message"]["content"]

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Groq API error: {e.response.status_code} - {e.response.text}"
            )
            raise RuntimeError(f"Groq API request failed: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Groq API request failed: {e}")
            raise

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 256,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stop_event: Optional[asyncio.Event] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """
        Generate text with streaming using Groq API

        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Top-p sampling
            stop_event: Event to stop generation
            **kwargs: Additional parameters

        Yields:
            Generated text chunks
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            async with self.client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": top_p,
                    "stream": True,
                },
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if stop_event and stop_event.is_set():
                        break

                    if not line or line.strip() == "":
                        continue

                    if line.startswith("data: "):
                        line = line[6:]  # Remove "data: " prefix

                    if line.strip() == "[DONE]":
                        break

                    try:
                        import json

                        data = json.loads(line)
                        delta = data["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

        except httpx.HTTPStatusError as e:
            logger.error(f"Groq API streaming error: {e.response.status_code}")
            raise RuntimeError(f"Groq API streaming failed: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Groq API streaming failed: {e}")
            raise

    async def get_available_models(self) -> list[Dict[str, Any]]:
        """
        Get list of available Groq models

        Returns:
            List of model information
        """
        try:
            response = await self.client.get(f"{self.base_url}/models")
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except Exception as e:
            logger.error(f"Failed to fetch Groq models: {e}")
            return []

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    def __del__(self):
        """Cleanup on deletion"""
        try:
            asyncio.create_task(self.close())
        except Exception:
            pass


# Available Groq models
GROQ_MODELS = {
    "llama-3.1-70b-versatile": {
        "name": "Llama 3.1 70B Versatile",
        "context_length": 131072,
        "description": "Fastest large model, great for most tasks",
    },
    "llama-3.1-8b-instant": {
        "name": "Llama 3.1 8B Instant",
        "context_length": 131072,
        "description": "Ultra-fast lightweight model",
    },
    "llama-3.2-90b-vision-preview": {
        "name": "Llama 3.2 90B Vision",
        "context_length": 8192,
        "description": "Vision-capable model (preview)",
    },
    "mixtral-8x7b-32768": {
        "name": "Mixtral 8x7B",
        "context_length": 32768,
        "description": "Mixture of Experts model",
    },
    "gemma2-9b-it": {
        "name": "Gemma 2 9B",
        "context_length": 8192,
        "description": "Google's Gemma model",
    },
}


def get_groq_backend(
    api_key: Optional[str] = None, model: str = "llama-3.1-70b-versatile"
) -> GroqLLMBackend:
    """
    Convenience function to create a Groq backend

    Args:
        api_key: Groq API key
        model: Model name

    Returns:
        GroqLLMBackend instance
    """
    return GroqLLMBackend(api_key=api_key, model=model)
