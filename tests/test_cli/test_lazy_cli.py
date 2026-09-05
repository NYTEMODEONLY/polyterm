"""Regression tests for lazy CLI loading."""

import importlib
import sys
from contextlib import contextmanager

from click.testing import CliRunner


def _restore_module(module_name, module):
    """Put a module back in sys.modules and on its parent package.

    unittest.mock.patch on Python 3.10 resolves 'polyterm.cli.main.Config'
    via getattr(polyterm.cli, 'main'), not sys.modules. Leaving a leftover
    reimport on the package attribute makes later CLI tests patch a Config
    that `cli` never instantiates.
    """
    sys.modules[module_name] = module
    parent_name, _, attr = module_name.rpartition(".")
    parent = sys.modules.get(parent_name)
    if parent is not None and attr:
        setattr(parent, attr, module)


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
                _restore_module(module_name, module)


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


def test_isolated_cli_main_restores_package_attribute_for_patch():
    """Later @patch('polyterm.cli.main.Config') must hit the live cli module."""
    import polyterm.cli
    import polyterm.cli.main as original

    with isolated_cli_main() as isolated:
        assert isolated is not original
        assert sys.modules["polyterm.cli.main"] is isolated

    restored = sys.modules["polyterm.cli.main"]
    assert restored is original
    assert polyterm.cli.main is original
