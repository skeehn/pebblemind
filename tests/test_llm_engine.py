"""Tests for LLM engine"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch, PropertyMock
from pathlib import Path

from pebblemind.config import LLMConfig
from pebblemind.core.llm import LLMEngine, MODEL_PATHS, MODEL_NAMES


@pytest.fixture
def llm_config():
    """Create LLM configuration for testing"""
    return LLMConfig(
        model_size="1.5b",
        model_path="",
        model_name="Qwen2.5-1.5B-Instruct",
        context_length=2048,
        max_tokens=256,
        temperature=0.7,
        top_p=0.9,
        top_k=40,
        threads=4,
        batch_size=512,
        enable_blas=True,
        blas_vendor="OpenBLAS",
        enable_gpu_offload=False,
        gpu_layers=0,
        auto_detect_gpu=False,
        enable_native=False
    )


@pytest.fixture
def mock_llama():
    """Create mock Llama instance"""
    mock = MagicMock()
    mock.create_chat_completion.return_value = {
        "choices": [
            {
                "message": {
                    "content": "Test response"
                }
            }
        ]
    }
    return mock


class TestLLMEngine:
    """Test LLM engine functionality"""

    def test_initialization(self, llm_config):
        """Test LLM engine initialization"""
        engine = LLMEngine(llm_config)
        assert engine.config == llm_config
        assert engine.model is None
        assert engine._initialized is False

    def test_model_path_resolution_with_size(self, llm_config):
        """Test model path resolution using model_size"""
        engine = LLMEngine(llm_config)
        path = engine._resolve_model_path()
        assert path == MODEL_PATHS["1.5b"]
        assert engine.config.model_name == MODEL_NAMES["1.5b"]

    def test_model_path_resolution_with_explicit_path(self, llm_config):
        """Test model path resolution with explicit path"""
        llm_config.model_path = "/custom/path/model.gguf"
        engine = LLMEngine(llm_config)
        path = engine._resolve_model_path()
        assert path == "/custom/path/model.gguf"

    def test_model_path_resolution_fallback(self, llm_config):
        """Test model path resolution fallback for unknown size"""
        llm_config.model_size = "unknown"
        engine = LLMEngine(llm_config)
        path = engine._resolve_model_path()
        assert path == MODEL_PATHS["3b"]
        assert engine.config.model_size == "3b"

    def test_validate_model_path_exists(self, llm_config, tmp_path):
        """Test model path validation when file exists"""
        model_file = tmp_path / "test_model.gguf"
        model_file.write_bytes(b"x" * (10 * 1024 * 1024))  # 10MB file

        engine = LLMEngine(llm_config)
        assert engine._validate_model_path(str(model_file)) is True

    def test_validate_model_path_not_exists(self, llm_config):
        """Test model path validation when file doesn't exist"""
        engine = LLMEngine(llm_config)
        assert engine._validate_model_path("/nonexistent/model.gguf") is False

    def test_detect_gpu_availability(self, llm_config):
        """Test GPU detection"""
        engine = LLMEngine(llm_config)
        result = engine._detect_gpu_availability()
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    @patch('pebblemind.core.llm.Llama', None)
    async def test_initialize_without_llama_cpp(self, llm_config):
        """Test initialization fails gracefully without any backend"""
        engine = LLMEngine(llm_config)

        with patch('pebblemind.core.llm.ollama_is_available', return_value=False), \
             patch.object(LLMEngine, '_hf_available', return_value=False):
            with pytest.raises(ImportError, match=r"No LLM backend available|llama-cpp-python"):
                await engine.initialize()

    @pytest.mark.asyncio
    async def test_initialize_ollama_backend(self, llm_config):
        """Test Ollama backend initializes when server answers"""
        from unittest.mock import MagicMock
        llm_config.backend = "ollama"
        engine = LLMEngine(llm_config)
        fake_resp = MagicMock()
        fake_resp.json.return_value = {"models": [{"name": "qwen2.5:1.5b"}]}
        fake_resp.raise_for_status.return_value = None
        with patch('httpx.get', return_value=fake_resp):
            await engine.initialize()
        assert engine.backend_name == "ollama"
        assert engine._is_ready()

    @pytest.mark.asyncio
    async def test_generate_without_initialization(self, llm_config):
        """Test generate fails without initialization"""
        engine = LLMEngine(llm_config)

        with pytest.raises(RuntimeError, match="LLM engine not initialized"):
            await engine.generate("Test message")

    @pytest.mark.asyncio
    @patch('pebblemind.core.llm.Llama')
    @patch('pebblemind.core.llm.Path')
    async def test_generate_with_mock(self, mock_path, mock_llama_class, llm_config):
        """Test text generation with mocked llama"""
        # Setup mocks
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.is_file.return_value = True
        mock_path_instance.stat.return_value.st_size = 1024 * 1024 * 1024  # 1GB
        mock_path.return_value = mock_path_instance

        mock_llama_instance = MagicMock()
        mock_llama_instance.create_chat_completion.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "Test response"
                    }
                }
            ]
        }
        mock_llama_class.return_value = mock_llama_instance

        # Test
        engine = LLMEngine(llm_config)
        await engine.initialize()
        result = await engine.generate("Test message")

        assert result == "Test response"
        assert mock_llama_instance.create_chat_completion.called

    @pytest.mark.asyncio
    @patch('pebblemind.core.llm.Llama')
    @patch('pebblemind.core.llm.Path')
    async def test_generate_with_context(self, mock_path, mock_llama_class, llm_config):
        """Test generation with context"""
        # Setup mocks
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.is_file.return_value = True
        mock_path_instance.stat.return_value.st_size = 1024 * 1024 * 1024
        mock_path.return_value = mock_path_instance

        mock_llama_instance = MagicMock()
        mock_llama_instance.create_chat_completion.return_value = {
            "choices": [{"message": {"content": "Response with context"}}]
        }
        mock_llama_class.return_value = mock_llama_instance

        # Test
        engine = LLMEngine(llm_config)
        await engine.initialize()
        result = await engine.generate(
            "Test message",
            context=["Context 1", "Context 2"]
        )

        assert result == "Response with context"

    @pytest.mark.asyncio
    @patch('pebblemind.core.llm.Llama')
    @patch('pebblemind.core.llm.Path')
    async def test_generate_stream_uses_same_prompt_context_and_caps(self, mock_path, mock_llama_class, llm_config):
        """Test streaming generation matches non-streaming prompt/context construction and caps"""
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.is_file.return_value = True
        mock_path_instance.stat.return_value.st_size = 1024 * 1024 * 1024
        mock_path.return_value = mock_path_instance

        mock_llama_instance = MagicMock()
        mock_llama_instance.create_chat_completion.return_value = [
            {"choices": [{"delta": {"content": "Hello"}}]},
            {"choices": [{"delta": {}}]},
        ]
        mock_llama_class.return_value = mock_llama_instance

        engine = LLMEngine(llm_config)
        await engine.initialize()

        chunks = []
        async for chunk in engine.generate_stream(
            "Test message",
            context=["Context 1", "Context 2", "Context 3", "Context 4"],
            max_tokens=999,
            temperature=0.95,
            top_p=0.99,
        ):
            chunks.append(chunk)

        assert chunks == ["Hello"]

        generation_params = mock_llama_instance.create_chat_completion.call_args.kwargs
        assert generation_params["stream"] is True
        assert generation_params["max_tokens"] == 256
        assert generation_params["temperature"] == 0.7
        assert generation_params["top_p"] == 0.9
        assert generation_params["stop"] == ["\n\n"]
        assert generation_params["messages"] == [
            {
                "role": "system",
                "content": (
                    "You are PebbleMind, a highly efficient AI assistant running on lightweight hardware. "
                    "Provide concise, accurate responses with clear reasoning. "
                    "Focus on being helpful while maintaining efficiency."
                ),
            },
            {"role": "system", "content": "Context: Context 2"},
            {"role": "system", "content": "Context: Context 3"},
            {"role": "system", "content": "Context: Context 4"},
            {"role": "user", "content": "Test message"},
        ]

    @pytest.mark.asyncio
    @patch('pebblemind.core.llm.Llama')
    @patch('pebblemind.core.llm.Path')
    async def test_switch_model(self, mock_path, mock_llama_class, llm_config):
        """Test model switching"""
        # Setup mocks
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.is_file.return_value = True
        mock_path_instance.stat.return_value.st_size = 1024 * 1024 * 1024
        mock_path.return_value = mock_path_instance

        mock_llama_class.return_value = MagicMock()

        # Test
        engine = LLMEngine(llm_config)
        await engine.initialize()

        result = await engine.switch_model("7b")
        assert result is True
        assert engine.config.model_size == "7b"
        assert engine.config.model_name == MODEL_NAMES["7b"]

    @pytest.mark.asyncio
    async def test_switch_model_invalid(self, llm_config):
        """Test switching to invalid model"""
        engine = LLMEngine(llm_config)
        result = await engine.switch_model("invalid")
        assert result is False

    @pytest.mark.asyncio
    @patch('pebblemind.core.llm.Llama')
    @patch('pebblemind.core.llm.Path')
    async def test_get_model_info(self, mock_path, mock_llama_class, llm_config):
        """Test getting model info"""
        # Setup mocks
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.is_file.return_value = True
        mock_path_instance.stat.return_value.st_size = 1024 * 1024 * 1024  # 1GB
        mock_path.return_value = mock_path_instance

        mock_llama_class.return_value = MagicMock()

        # Test
        engine = LLMEngine(llm_config)
        await engine.initialize()
        info = await engine.get_model_info()

        assert info["status"] == "loaded"
        assert info["model_size"] == "1.5b"
        assert info["blas_enabled"] is True
        assert "file_size_gb" in info

    @pytest.mark.asyncio
    async def test_cleanup(self, llm_config):
        """Test cleanup"""
        engine = LLMEngine(llm_config)
        await engine.cleanup()
        assert engine.model is None
        assert engine._initialized is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
