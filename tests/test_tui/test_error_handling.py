"""Tests for TUI error handling and display

Phase 2 of POL-3: Verify that handle_api_error produces structured
user-friendly output for different error categories.
"""

import io
import pytest
from unittest.mock import Mock, patch, call
from rich.console import Console

from polyterm.utils.errors import (
    handle_api_error,
    display_error,
    show_error,
    handle_validation_error,
    handle_config_error,
    handle_network_error,
    PolyTermError,
    APIError,
    ConfigError,
    ValidationError,
    NetworkError,
    ERROR_MESSAGES,
)


def _capture_output(func, *args, **kwargs):
    """Run a function with a real Rich Console capturing to a string buffer."""
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=True, width=120)
    func(console, *args, **kwargs)
    return buf.getvalue()


class TestHandleApiError:
    """Tests for handle_api_error error categorization"""

    def test_timeout_error_shows_timeout_title(self):
        output = _capture_output(handle_api_error, Exception("request timed out"), "market data")
        assert "Timeout" in output

    def test_timeout_includes_context(self):
        output = _capture_output(handle_api_error, Exception("timed out"), "whale tracking")
        assert "whale tracking" in output

    def test_connection_error_shows_connection_title(self):
        output = _capture_output(handle_api_error, Exception("Connection refused"), "data")
        assert "Connection" in output

    def test_404_error_shows_not_found(self):
        output = _capture_output(handle_api_error, Exception("HTTP 404 not found"), "lookup")
        assert "Not Found" in output

    def test_403_error_shows_access_denied(self):
        output = _capture_output(handle_api_error, Exception("403 Forbidden"), "API")
        assert "Access Denied" in output

    def test_429_rate_limit_detected(self):
        output = _capture_output(handle_api_error, Exception("429 Too Many Requests"), "API")
        assert "Rate Limited" in output

    def test_500_server_error_detected(self):
        output = _capture_output(handle_api_error, Exception("500 Internal Server Error"), "API")
        assert "Server Error" in output

    def test_generic_error_fallback(self):
        output = _capture_output(handle_api_error, Exception("something weird"), "API")
        assert "API Error" in output

    def test_generic_error_includes_details(self):
        output = _capture_output(handle_api_error, Exception("weird thing"), "API")
        assert "weird thing" in output

    def test_suggestion_always_present(self):
        """Every error category includes a suggestion"""
        for msg in ["timed out", "Connection refused", "404", "403", "429", "500", "other"]:
            output = _capture_output(handle_api_error, Exception(msg), "test")
            assert "Suggestion" in output or "suggestion" in output.lower() or "try" in output.lower(), \
                f"No suggestion for error: {msg}"


class TestDisplayError:
    """Tests for display_error formatting"""

    def test_basic_error_display(self):
        output = _capture_output(display_error, "Test Error", "Something went wrong")
        assert "Something went wrong" in output

    def test_error_with_suggestion(self):
        output = _capture_output(display_error, "Error", "Bad input", suggestion="Try again")
        assert "Try again" in output

    def test_error_with_details(self):
        output = _capture_output(display_error, "Error", "Failed", details="errno 111")
        assert "errno 111" in output

    def test_title_in_output(self):
        output = _capture_output(display_error, "Big Error", "Broke things")
        assert "Big Error" in output


class TestShowError:
    """Tests for predefined error messages"""

    def test_known_error_key(self):
        output = _capture_output(show_error, "no_markets_found")
        assert "No Markets Found" in output

    def test_unknown_error_key(self):
        output = _capture_output(show_error, "totally_unknown_key")
        assert "unexpected" in output.lower() or "error" in output.lower()

    def test_all_predefined_messages_are_complete(self):
        for key, msg in ERROR_MESSAGES.items():
            assert "title" in msg, f"{key} missing title"
            assert "message" in msg, f"{key} missing message"

    def test_show_error_with_details(self):
        output = _capture_output(show_error, "database_error", details="SQLITE_LOCKED")
        assert "SQLITE_LOCKED" in output


class TestErrorExceptionClasses:
    """Tests for custom exception classes"""

    def test_polyterm_error_has_fields(self):
        err = PolyTermError("msg", suggestion="fix", details="detail")
        assert err.message == "msg"
        assert err.suggestion == "fix"
        assert err.details == "detail"

    def test_api_error_is_polyterm_error(self):
        assert issubclass(APIError, PolyTermError)

    def test_config_error_is_polyterm_error(self):
        assert issubclass(ConfigError, PolyTermError)

    def test_validation_error_is_polyterm_error(self):
        assert issubclass(ValidationError, PolyTermError)

    def test_network_error_is_polyterm_error(self):
        assert issubclass(NetworkError, PolyTermError)


class TestHandleValidationError:

    def test_displays_invalid_input(self):
        output = _capture_output(handle_validation_error, "price", "abc", "a number between 0 and 1")
        assert "abc" in output
        assert "price" in output


class TestHandleConfigError:

    def test_displays_config_error(self):
        output = _capture_output(handle_config_error, Exception("TOML parse error"))
        assert "Configuration" in output


class TestHandleNetworkError:

    def test_displays_network_error(self):
        output = _capture_output(handle_network_error, Exception("DNS resolution failed"))
        assert "Network" in output


class TestScreenErrorHandlingIntegration:
    """Integration tests: verify screens pass API errors through handle_api_error.

    Screens NOT using handle_api_error (report to TUI Developer for POL-4):
    - settings.py (bare except for PyPI version check)
    - market_picker.py (bare except, swallows GammaClient errors silently)
    """

    @patch('polyterm.tui.screens.analytics.APIAggregator')
    @patch('polyterm.tui.screens.analytics.CLOBClient')
    @patch('polyterm.tui.screens.analytics.GammaClient')
    @patch('polyterm.tui.screens.analytics.Config')
    @patch('polyterm.tui.screens.analytics.handle_api_error')
    def test_analytics_screen_calls_handle_api_error_on_failure(
        self, mock_handle, mock_config, mock_gamma, mock_clob, mock_aggregator
    ):
        """Analytics screen routes API exceptions through handle_api_error"""
        from polyterm.tui.screens.analytics import _display_trending_markets

        mock_config.return_value = Mock(
            gamma_base_url="https://test", gamma_api_key="",
            clob_rest_endpoint="https://test", clob_endpoint="wss://test",
        )
        mock_agg = Mock()
        mock_agg.get_top_markets_by_volume.side_effect = Exception("API timeout")
        mock_aggregator.return_value = mock_agg

        console = Mock()
        # Support console.status() context manager used by loading spinner
        console.status.return_value.__enter__ = Mock(return_value=None)
        console.status.return_value.__exit__ = Mock(return_value=False)
        _display_trending_markets(console, limit=10)

        mock_handle.assert_called_once()
        args = mock_handle.call_args[0]
        assert args[0] is console
        assert "timeout" in str(args[1]).lower()
        assert args[2] == "market analytics"

    @patch('polyterm.tui.screens.predictions.handle_api_error')
    @patch('polyterm.tui.screens.predictions.subprocess.run')
    def test_predictions_screen_calls_handle_api_error_on_failure(
        self, mock_run, mock_handle
    ):
        """Predictions screen routes subprocess errors through handle_api_error"""
        from polyterm.tui.screens.predictions import predictions_screen

        mock_run.side_effect = Exception("Connection refused")
        console = Mock()
        # Inputs: choice=1, limit=5, horizon=24, min_confidence=0.5
        console.input.side_effect = ["1", "5", "24", "0.5"]

        predictions_screen(console)

        mock_handle.assert_called_once()
        args = mock_handle.call_args[0]
        assert args[0] is console
        assert args[2] == "predictions"
