"""Tests for CLI commands"""

import pytest
from click.testing import CliRunner
from unittest.mock import Mock, patch, MagicMock
from polyterm.cli.main import cli


class TestCLI:
    """Test CLI main entry point"""
    
    @pytest.fixture
    def runner(self):
        """Create CLI test runner"""
        return CliRunner()
    
    def test_cli_version(self, runner):
        """Test CLI version command"""
        import polyterm
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert polyterm.__version__ in result.output
    
    def test_cli_help(self, runner):
        """Test CLI help"""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "PolyTerm" in result.output
        assert "monitor" in result.output
        assert "watch" in result.output


class TestConfigCommand:
    """Test config command"""
    
    @pytest.fixture
    def runner(self):
        return CliRunner()
    
    @patch('polyterm.cli.commands.config_cmd.Config')
    def test_config_list(self, mock_config, runner):
        """Test listing configuration"""
        mock_instance = Mock()
        mock_instance.config = {"alerts": {"probability_threshold": 10.0}}
        mock_config.return_value = mock_instance
        
        result = runner.invoke(cli, ["config", "--list"])
        assert result.exit_code == 0
    
    def test_config_set(self, runner, tmp_path, monkeypatch):
        """Test setting configuration value"""
        # Use a temp config file to avoid polluting real config
        temp_config = tmp_path / "config.toml"
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        result = runner.invoke(cli, ["config", "--set", "alerts.probability_threshold", "20"])
        assert result.exit_code == 0
        assert "20" in result.output

    def test_config_get(self, runner):
        """Test getting configuration value"""
        # Test that config get returns a value (don't check specific value as it depends on user config)
        result = runner.invoke(cli, ["config", "--get", "alerts.probability_threshold"])
        assert result.exit_code == 0
        assert "alerts.probability_threshold" in result.output


class TestExportCommand:
    """Test export command"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @patch('polyterm.cli.commands.export_cmd.GammaClient')
    @patch('polyterm.cli.commands.export_cmd.CLOBClient')
    def test_export_json(self, mock_clob, mock_gamma, runner):
        """Test exporting data as JSON"""
        # Mock API responses
        mock_gamma_instance = Mock()
        mock_gamma_instance.get_market.return_value = {
            "id": "market1",
            "question": "Test Market",
            "slug": "test-market",
            "description": "Test description",
            "endDate": "2026-12-31",
            "active": True,
            "closed": False,
            "volume": 1000,
            "volume24hr": 100,
            "volume1wk": 500,
            "volume1mo": 800,
            "liquidity": 500,
            "outcomePrices": '["0.65", "0.35"]',
            "spread": 0.01,
            "bestBid": 0.64,
            "bestAsk": 0.66,
            "oneHourPriceChange": 0.01,
            "oneDayPriceChange": 0.02,
            "oneWeekPriceChange": 0.03,
            "oneMonthPriceChange": 0.05,
        }
        mock_gamma.return_value = mock_gamma_instance

        result = runner.invoke(cli, ["export", "--market", "market1", "--format", "json"])

        # Should output JSON
        assert result.exit_code == 0
        assert "market" in result.output

    @patch('polyterm.cli.commands.export_cmd.GammaClient')
    @patch('polyterm.cli.commands.export_cmd.CLOBClient')
    def test_export_csv(self, mock_clob, mock_gamma, runner):
        """Test exporting data as CSV"""
        mock_gamma_instance = Mock()
        mock_gamma_instance.get_market.return_value = {
            "id": "market1",
            "question": "Test Market",
            "slug": "test-market",
            "description": "Test description",
            "endDate": "2026-12-31",
            "active": True,
            "closed": False,
            "volume": 1000,
            "volume24hr": 100,
            "liquidity": 500,
            "outcomePrices": '["0.65", "0.35"]',
            "spread": 0.01,
            "oneHourPriceChange": 0.01,
            "oneDayPriceChange": 0.02,
        }
        mock_gamma.return_value = mock_gamma_instance

        result = runner.invoke(cli, ["export", "--market", "market1", "--format", "csv"])

        assert result.exit_code == 0
        assert "id,question" in result.output


class TestUtilityFunctions:
    """Test utility functions"""
    
    def test_format_probability(self):
        """Test probability formatting"""
        from polyterm.utils.formatting import format_probability
        
        result = format_probability(65.5)
        assert "65.5%" in result
        
        result_with_change = format_probability(65.5, 60.0)
        assert "65.5%" in result_with_change
        assert "+5.5%" in result_with_change or "5.5%" in result_with_change
    
    def test_format_volume(self):
        """Test volume formatting"""
        from polyterm.utils.formatting import format_volume
        
        assert format_volume(1500) == "1.50K"
        assert format_volume(1500000) == "1.50M"
        assert format_volume(1500000000) == "1.50B"
    
    def test_format_timestamp(self):
        """Test timestamp formatting"""
        from polyterm.utils.formatting import format_timestamp
        
        result = format_timestamp(1234567890, include_time=True)
        assert len(result) > 0
        assert ":" in result  # Should include time
        
        result_date_only = format_timestamp(1234567890, include_time=False)
        assert ":" not in result_date_only  # Should not include time
    
    def test_format_duration(self):
        """Test duration formatting"""
        from polyterm.utils.formatting import format_duration
        
        assert format_duration(30) == "30s"
        assert format_duration(120) == "2m"
        assert format_duration(3600) == "1h"
        assert format_duration(86400) == "1d"


class TestConfigManagement:
    """Test configuration management"""

    def test_config_initialization(self, tmp_path):
        """Test config initializes with defaults when no config file exists"""
        # Force reimport to clear any cached state
        import importlib
        import polyterm.utils.config
        importlib.reload(polyterm.utils.config)
        from polyterm.utils.config import Config

        # Use temp path that doesn't exist to force defaults
        config_file = tmp_path / "nonexistent" / "config.toml"
        config = Config(config_path=str(config_file))

        # Should use defaults when config file doesn't exist
        assert config.probability_threshold == 10.0
        assert config.volume_threshold == 50.0
        assert config.check_interval == 60

    def test_config_get_set(self, tmp_path):
        """Test config get/set operations"""
        from polyterm.utils.config import Config

        config_file = tmp_path / "config.toml"
        config = Config(config_path=str(config_file))

        config.set("alerts.probability_threshold", 15.0)
        assert config.get("alerts.probability_threshold") == 15.0

    def test_config_nested_values(self, tmp_path):
        """Test nested configuration values"""
        from polyterm.utils.config import Config

        config_file = tmp_path / "config.toml"
        config = Config(config_path=str(config_file))

        config.set("custom.nested.value", 100)
        assert config.get("custom.nested.value") == 100

