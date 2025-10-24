"""Unit tests for Configuration System"""

import pytest
import yaml
from pathlib import Path
from pydantic import ValidationError

from pebblemind.config import (
    LLMConfig,
    RAGConfig,
    VoiceConfig,
    MemoryConfig,
    ToolsConfig,
    APIConfig,
    PebbleMindConfig,
    load_config,
    save_config
)


@pytest.mark.unit
class TestLLMConfig:
    """Test suite for LLM Configuration"""

    def test_llm_config_defaults(self):
        """Test LLM config with defaults"""
        config = LLMConfig(model_path="models/test.gguf")

        assert config.model_path == "models/test.gguf"
        assert config.model_size == "3b"
        assert config.context_length == 2048
        assert config.temperature == 0.7
        assert config.enable_blas is True
        assert config.threads == -1

    def test_llm_config_custom_values(self):
        """Test LLM config with custom values"""
        config = LLMConfig(
            model_path="models/custom.gguf",
            model_size="7b",
            context_length=4096,
            temperature=0.9,
            enable_blas=False,
            threads=8
        )

        assert config.model_size == "7b"
        assert config.context_length == 4096
        assert config.temperature == 0.9
        assert config.enable_blas is False
        assert config.threads == 8

    def test_llm_config_validation(self):
        """Test LLM config validation"""
        # Invalid temperature
        with pytest.raises(ValidationError):
            LLMConfig(model_path="test.gguf", temperature=3.0)

        # Invalid model size
        with pytest.raises(ValidationError):
            LLMConfig(model_path="test.gguf", model_size="invalid")


@pytest.mark.unit
class TestRAGConfig:
    """Test suite for RAG Configuration"""

    def test_rag_config_defaults(self):
        """Test RAG config with defaults"""
        config = RAGConfig()

        assert config.embedding_model == "BAAI/bge-small-en-v1.5"
        assert config.chunk_size == 512
        assert config.chunk_overlap == 32
        assert config.max_results == 3
        assert config.embedding_dim == 384

    def test_rag_config_custom_values(self):
        """Test RAG config with custom values"""
        config = RAGConfig(
            embedding_model="custom/model",
            chunk_size=256,
            chunk_overlap=64,
            max_results=5,
            embedding_dim=768
        )

        assert config.embedding_model == "custom/model"
        assert config.chunk_size == 256
        assert config.chunk_overlap == 64
        assert config.max_results == 5
        assert config.embedding_dim == 768


@pytest.mark.unit
class TestMemoryConfig:
    """Test suite for Memory Configuration"""

    def test_memory_config_defaults(self):
        """Test memory config with defaults"""
        config = MemoryConfig()

        assert config.consolidation_period_days == 7
        assert config.forget_threshold_importance == 0.2
        assert config.forget_threshold_age_days == 30
        assert config.max_to_forget_per_session == 10

    def test_memory_config_validation(self):
        """Test memory config validation"""
        # Valid config
        config = MemoryConfig(
            consolidation_period_days=14,
            forget_threshold_importance=0.5,
            forget_threshold_age_days=60
        )
        assert config.consolidation_period_days == 14


@pytest.mark.unit
class TestToolsConfig:
    """Test suite for Tools Configuration"""

    def test_tools_config_defaults(self):
        """Test tools config with defaults"""
        config = ToolsConfig()

        assert config.enabled is True
        assert config.allow_code_execution is True
        assert config.allow_file_access is True
        assert config.web_search_enabled is True

    def test_tools_config_security_settings(self):
        """Test tools config with restricted security settings"""
        config = ToolsConfig(
            enabled=True,
            allow_code_execution=False,
            allow_file_access=False,
            web_search_enabled=False
        )

        assert config.enabled is True
        assert config.allow_code_execution is False
        assert config.allow_file_access is False
        assert config.web_search_enabled is False


@pytest.mark.unit
class TestAPIConfig:
    """Test suite for API Configuration"""

    def test_api_config_defaults(self):
        """Test API config with defaults"""
        config = APIConfig()

        assert config.host == "localhost"
        assert config.port == 8000
        assert config.cors_origins == ["*"]

    def test_api_config_custom_values(self):
        """Test API config with custom values"""
        config = APIConfig(
            host="0.0.0.0",
            port=9000,
            cors_origins=["http://localhost:3000"]
        )

        assert config.host == "0.0.0.0"
        assert config.port == 9000
        assert config.cors_origins == ["http://localhost:3000"]


@pytest.mark.unit
class TestPebbleMindConfig:
    """Test suite for main PebbleMind Configuration"""

    def test_pebblemind_config_creation(self):
        """Test creating a complete PebbleMind config"""
        config = PebbleMindConfig(
            llm=LLMConfig(model_path="models/test.gguf"),
            rag=RAGConfig(),
            voice=VoiceConfig(),
            memory=MemoryConfig(),
            tools=ToolsConfig(),
            api=APIConfig()
        )

        assert config.llm.model_path == "models/test.gguf"
        assert config.rag.embedding_model == "BAAI/bge-small-en-v1.5"
        assert config.voice.stt_model == "base.en"
        assert config.memory.consolidation_period_days == 7
        assert config.tools.enabled is True
        assert config.api.port == 8000

    def test_pebblemind_config_defaults(self):
        """Test that PebbleMind config uses defaults"""
        config = PebbleMindConfig()

        assert config.llm is not None
        assert config.rag is not None
        assert config.voice is not None
        assert config.memory is not None
        assert config.tools is not None
        assert config.api is not None


@pytest.mark.unit
class TestConfigLoading:
    """Test suite for config loading and saving"""

    def test_save_and_load_config(self, temp_dir):
        """Test saving and loading configuration"""
        config_path = temp_dir / "test_config.yaml"

        # Create config
        original_config = PebbleMindConfig(
            llm=LLMConfig(
                model_path="models/test.gguf",
                model_size="3b",
                temperature=0.8
            ),
            rag=RAGConfig(chunk_size=256),
            tools=ToolsConfig(allow_code_execution=False)
        )

        # Save config
        save_config(original_config, config_path)

        # Load config
        loaded_config = load_config(config_path)

        # Verify
        assert loaded_config.llm.model_path == "models/test.gguf"
        assert loaded_config.llm.model_size == "3b"
        assert loaded_config.llm.temperature == 0.8
        assert loaded_config.rag.chunk_size == 256
        assert loaded_config.tools.allow_code_execution is False

    def test_load_nonexistent_config_creates_default(self, temp_dir):
        """Test that loading nonexistent config creates default"""
        config_path = temp_dir / "nonexistent.yaml"

        config = load_config(config_path)

        # Should return default config
        assert config.llm is not None
        assert config.rag is not None

    def test_load_invalid_yaml_raises_error(self, temp_dir):
        """Test that invalid YAML raises an error"""
        config_path = temp_dir / "invalid.yaml"
        config_path.write_text("invalid: yaml: content:")

        with pytest.raises(Exception):
            load_config(config_path)

    def test_config_yaml_structure(self, temp_dir):
        """Test that saved config has correct YAML structure"""
        config_path = temp_dir / "test_config.yaml"

        config = PebbleMindConfig(
            llm=LLMConfig(model_path="models/test.gguf"),
            rag=RAGConfig()
        )

        save_config(config, config_path)

        # Load as raw YAML
        with open(config_path) as f:
            yaml_data = yaml.safe_load(f)

        # Verify structure
        assert "llm" in yaml_data
        assert "rag" in yaml_data
        assert "model_path" in yaml_data["llm"]
        assert "embedding_model" in yaml_data["rag"]


@pytest.mark.unit
class TestConfigValidation:
    """Test suite for configuration validation"""

    def test_llm_config_validates_model_path(self):
        """Test that LLM config validates model path"""
        # Empty model path should fail
        with pytest.raises(ValidationError):
            LLMConfig(model_path="")

    def test_llm_config_validates_temperature_range(self):
        """Test that temperature is validated"""
        # Too high
        with pytest.raises(ValidationError):
            LLMConfig(model_path="test.gguf", temperature=3.0)

        # Negative
        with pytest.raises(ValidationError):
            LLMConfig(model_path="test.gguf", temperature=-0.5)

    def test_api_config_validates_port_range(self):
        """Test that API port is validated"""
        # Valid port
        config = APIConfig(port=8080)
        assert config.port == 8080

        # Invalid port (too high)
        with pytest.raises(ValidationError):
            APIConfig(port=70000)

        # Invalid port (negative)
        with pytest.raises(ValidationError):
            APIConfig(port=-1)

    def test_rag_config_validates_positive_values(self):
        """Test that RAG config validates positive values"""
        # Valid
        config = RAGConfig(chunk_size=256, chunk_overlap=32)
        assert config.chunk_size == 256

        # Invalid chunk size
        with pytest.raises(ValidationError):
            RAGConfig(chunk_size=-1)

        # Invalid overlap
        with pytest.raises(ValidationError):
            RAGConfig(chunk_overlap=-1)
