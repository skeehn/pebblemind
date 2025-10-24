"""Pytest configuration and shared fixtures for PebbleMind tests"""

import asyncio
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock
from typing import Generator, Dict, Any

# Import PebbleMind components
from pebblemind.config import (
    PebbleMindConfig,
    LLMConfig,
    RAGConfig,
    VoiceConfig,
    MemoryConfig,
    ToolsConfig,
    APIConfig
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the entire test session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # Cleanup
    if temp_path.exists():
        shutil.rmtree(temp_path)


@pytest.fixture
def test_config(temp_dir: Path) -> PebbleMindConfig:
    """Create a test configuration with temporary paths"""
    return PebbleMindConfig(
        llm=LLMConfig(
            model_path=str(temp_dir / "test_model.gguf"),
            model_size="1.5b",
            context_length=512,  # Smaller for tests
            max_tokens=100,
            temperature=0.7,
            enable_blas=False,  # Disable for tests
            enable_gpu_offload=False,
            gpu_layers=0,
            threads=2
        ),
        rag=RAGConfig(
            embedding_model="BAAI/bge-small-en-v1.5",
            vector_db_path=str(temp_dir / "test_vectors.db"),
            chunk_size=128,
            chunk_overlap=16,
            max_results=3,
            embedding_dim=384
        ),
        voice=VoiceConfig(
            stt_model="base.en",
            tts_model="amy-low",
            sample_rate=16000
        ),
        memory=MemoryConfig(
            long_term_db_path=str(temp_dir / "test_memory.db"),
            consolidation_period_days=7,
            forget_threshold_importance=0.2,
            forget_threshold_age_days=30,
            max_to_forget_per_session=10
        ),
        tools=ToolsConfig(
            enabled=True,
            allow_code_execution=False,  # Disable for safety in tests
            allow_file_access=True,
            web_search_enabled=False  # Disable network calls in tests
        ),
        api=APIConfig(
            host="localhost",
            port=8000,
            cors_origins=["*"]
        )
    )


@pytest.fixture
def llm_config(temp_dir: Path) -> LLMConfig:
    """Create a test LLM configuration"""
    return LLMConfig(
        model_path=str(temp_dir / "test_model.gguf"),
        model_size="1.5b",
        context_length=512,
        max_tokens=100,
        temperature=0.7,
        enable_blas=False,
        enable_gpu_offload=False,
        gpu_layers=0,
        threads=2
    )


@pytest.fixture
def rag_config(temp_dir: Path) -> RAGConfig:
    """Create a test RAG configuration"""
    return RAGConfig(
        embedding_model="BAAI/bge-small-en-v1.5",
        vector_db_path=str(temp_dir / "test_vectors.db"),
        chunk_size=128,
        chunk_overlap=16,
        max_results=3,
        embedding_dim=384
    )


@pytest.fixture
def memory_config(temp_dir: Path) -> MemoryConfig:
    """Create a test memory configuration"""
    return MemoryConfig(
        long_term_db_path=str(temp_dir / "test_memory.db"),
        consolidation_period_days=7,
        forget_threshold_importance=0.2,
        forget_threshold_age_days=30,
        max_to_forget_per_session=10
    )


@pytest.fixture
def mock_llm():
    """Create a mock LLM for testing"""
    llm = MagicMock()
    llm.generate = Mock(return_value="Mock LLM response")
    llm.generate_async = Mock(return_value=asyncio.coroutine(lambda: "Mock async response")())
    llm.stream_generate = Mock(return_value=iter(["Mock", " streaming", " response"]))
    return llm


@pytest.fixture
def mock_embedding_model():
    """Create a mock embedding model for testing"""
    import numpy as np

    model = MagicMock()
    # Return a mock embedding vector
    model.encode = Mock(return_value=np.random.rand(1, 384).astype(np.float32))
    return model


@pytest.fixture
def sample_documents() -> list[Dict[str, Any]]:
    """Sample documents for RAG testing"""
    return [
        {
            "content": "Python is a high-level programming language known for its simplicity and readability.",
            "metadata": {"source": "test", "topic": "programming"}
        },
        {
            "content": "Machine learning is a subset of artificial intelligence that focuses on data and algorithms.",
            "metadata": {"source": "test", "topic": "ai"}
        },
        {
            "content": "The Transformer architecture revolutionized natural language processing with attention mechanisms.",
            "metadata": {"source": "test", "topic": "nlp"}
        }
    ]


@pytest.fixture
def sample_chat_messages() -> list[Dict[str, str]]:
    """Sample chat messages for testing"""
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"},
        {"role": "assistant", "content": "I'm doing well, thank you!"},
        {"role": "user", "content": "Can you help me with Python?"}
    ]


@pytest.fixture
async def mock_api_client():
    """Create a mock API client for testing"""
    from fastapi.testclient import TestClient
    # This will be used when we test the API
    # For now, return a mock
    return MagicMock()


@pytest.fixture
def calculator_expressions() -> Dict[str, Any]:
    """Test cases for calculator tool"""
    return {
        "valid": [
            ("2 + 2", 4),
            ("10 - 3", 7),
            ("5 * 6", 30),
            ("15 / 3", 5),
            ("2 ** 3", 8),
            ("(2 + 3) * 4", 20),
            ("10 % 3", 1)
        ],
        "invalid": [
            "import os",
            "__import__('os')",
            "exec('print(1)')",
            "eval('1+1')",
            "2 + ; rm -rf /",  # Injection attempt
        ]
    }


@pytest.fixture
def safe_code_samples() -> Dict[str, list[str]]:
    """Test cases for code executor tool"""
    return {
        "safe": [
            "x = 2 + 2\nprint(x)",
            "numbers = [1, 2, 3, 4, 5]\nprint(sum(numbers))",
            "result = max([10, 20, 30])\nprint(result)"
        ],
        "unsafe": [
            "import os\nos.system('ls')",
            "open('/etc/passwd', 'r').read()",
            "exec('malicious code')",
            "__import__('subprocess').call(['ls'])"
        ]
    }


# Async test support
@pytest.fixture
def async_test():
    """Decorator for async tests"""
    def decorator(func):
        return pytest.mark.asyncio(func)
    return decorator


# Mock sentence transformers to avoid downloading models during tests
@pytest.fixture(autouse=True)
def mock_sentence_transformers(monkeypatch):
    """Mock sentence transformers to avoid model downloads in tests"""
    import numpy as np

    class MockSentenceTransformer:
        def __init__(self, *args, **kwargs):
            pass

        def encode(self, texts, **kwargs):
            # Return random embeddings with correct shape
            if isinstance(texts, str):
                texts = [texts]
            return np.random.rand(len(texts), 384).astype(np.float32)

    # Only mock if sentence_transformers is imported
    try:
        import sentence_transformers
        monkeypatch.setattr(
            "sentence_transformers.SentenceTransformer",
            MockSentenceTransformer
        )
    except ImportError:
        pass
