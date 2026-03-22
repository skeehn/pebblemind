from pebblemind.config import Config


class TestConfig:
    def test_from_file_returns_defaults_for_missing_file(self, tmp_path):
        config = Config.from_file(str(tmp_path / "missing.yaml"))

        assert isinstance(config, Config)
        assert config.log_level == "INFO"
        assert config.api.port == 8000

    def test_from_file_returns_defaults_for_empty_file(self, tmp_path):
        config_path = tmp_path / "empty.yaml"
        config_path.write_text("")

        config = Config.from_file(str(config_path))

        assert isinstance(config, Config)
        assert config.log_level == "INFO"
        assert config.api.port == 8000

    def test_from_file_loads_values_from_yaml(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        config_path.write_text(
            "llm:\n"
            "  model_size: 3b\n"
            "api:\n"
            "  port: 9000\n"
        )

        config = Config.from_file(str(config_path))

        assert config.llm.model_size == "3b"
        assert config.api.port == 9000
