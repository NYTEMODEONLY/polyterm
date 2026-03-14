"""Regression tests for lazy CLI loading."""

import importlib
import sys
from contextlib import contextmanager

from click.testing import CliRunner


@contextmanager
def isolated_cli_main():
    target_modules = (
        "polyterm.cli.main",
        "polyterm.utils.config",
        "polyterm.cli.commands.monitor",
        "polyterm.cli.commands.whales",
    )
    original_modules = {module_name: sys.modules.get(module_name) for module_name in target_modules}

    for module_name in target_modules:
        sys.modules.pop(module_name, None)

    try:
        yield importlib.import_module("polyterm.cli.main")
    finally:
        for module_name in target_modules:
            sys.modules.pop(module_name, None)

        for module_name, module in original_modules.items():
            if module is not None:
                sys.modules[module_name] = module


def test_version_does_not_import_config_or_commands():
    with isolated_cli_main() as main:
        assert "polyterm.utils.config" not in sys.modules
        assert "polyterm.cli.commands.monitor" not in sys.modules

        runner = CliRunner()
        result = runner.invoke(main.cli, ["--version"])

        assert result.exit_code == 0
        assert "polyterm.utils.config" not in sys.modules
        assert "polyterm.cli.commands.monitor" not in sys.modules


def test_subcommand_help_imports_only_requested_command():
    with isolated_cli_main() as main:
        runner = CliRunner()
        result = runner.invoke(main.cli, ["monitor", "--help"])

        assert result.exit_code == 0
        assert "polyterm.cli.commands.monitor" in sys.modules
        assert "polyterm.cli.commands.whales" not in sys.modules
