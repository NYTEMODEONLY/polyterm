"""Tests for Config utility"""

import pytest
from pathlib import Path
from polyterm.utils.config import Config


class TestConfig:
    """Test Config class"""

    def test_default_config_loaded(self, tmp_path):
        """Config should have default values when no file exists"""
        config = Config(config_path=tmp_path / "nonexistent.toml")
        # Should have default values
        assert config.gamma_base_url != ""
        assert isinstance(config.config, dict)

    def test_get_dot_notation(self, tmp_path):
        """Config.get() should support dot notation"""
        config = Config(config_path=tmp_path / "test.toml")
        # API section should exist in defaults
        result = config.get("api.gamma_base_url")
        assert isinstance(result, str)

    def test_get_missing_key_returns_default(self, tmp_path):
        """Config.get() with missing key should return default"""
        config = Config(config_path=tmp_path / "test.toml")
        result = config.get("nonexistent.key", "fallback")
        assert result == "fallback"

    def test_set_and_get(self, tmp_path):
        """Config.set() should update values retrievable by get()"""
        config = Config(config_path=tmp_path / "test.toml")
        config.set("test_key", "test_value")
        assert config.get("test_key") == "test_value"

    def test_set_nested_key(self, tmp_path):
        """Config.set() should create nested structure"""
        config = Config(config_path=tmp_path / "test.toml")
        config.set("section.subsection.key", "deep_value")
        assert config.get("section.subsection.key") == "deep_value"

    def test_set_overwrites_non_dict_intermediate(self, tmp_path):
        """Config.set() should handle case where intermediate key is a non-dict value"""
        config = Config(config_path=tmp_path / "test.toml")
        config.set("flat_key", "string_value")
        # Now set a nested key under what was a string
        config.set("flat_key.nested", "new_value")
        assert config.get("flat_key.nested") == "new_value"

    def test_set_with_validation(self, tmp_path):
        """Config.set() should validate values against rules"""
        config = Config(config_path=tmp_path / "test.toml")
        # alerts.probability_threshold has a validation rule (float, 0.01, 1.0)
        config.set("alerts.probability_threshold", 0.5)
        assert config.get("alerts.probability_threshold") == 0.5

    def test_set_validation_rejects_out_of_range(self, tmp_path):
        """Config.set() should reject out-of-range values"""
        config = Config(config_path=tmp_path / "test.toml")
        with pytest.raises(ValueError):
            config.set("display.max_markets", 0)  # Min is 1

    def test_properties(self, tmp_path):
        """Config properties should return correct types"""
        config = Config(config_path=tmp_path / "test.toml")
        assert isinstance(config.gamma_api_key, str)
        assert isinstance(config.gamma_base_url, str)

    def test_save_and_reload(self, tmp_path):
        """Config should persist after save and reload"""
        config_path = tmp_path / "test.toml"
        config1 = Config(config_path=config_path)
        config1.set("test_key", "persisted_value")
        config1.save()

        config2 = Config(config_path=config_path)
        assert config2.get("test_key") == "persisted_value"
