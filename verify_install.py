#!/usr/bin/env python3
"""
Verification script to check PolyTerm installation
"""

import sys
import importlib

def check_module(module_name):
    """Check if a module can be imported"""
    try:
        importlib.import_module(module_name)
        print(f"✓ {module_name}")
        return True
    except ImportError as e:
        print(f"✗ {module_name}: {e}")
        return False

def main():
    print("PolyTerm Installation Verification")
    print("=" * 50)
    
    # Check core modules
    print("\nCore Modules:")
    modules = [
        "polyterm",
        "polyterm.api.gamma",
        "polyterm.api.clob",
        "polyterm.api.subgraph",
        "polyterm.core.scanner",
        "polyterm.core.alerts",
        "polyterm.core.analytics",
        "polyterm.utils.config",
        "polyterm.utils.formatting",
    ]
    
    core_ok = all(check_module(m) for m in modules)
    
    # Check CLI modules
    print("\nCLI Modules:")
    cli_modules = [
        "polyterm.cli.main",
        "polyterm.cli.commands.monitor",
        "polyterm.cli.commands.watch",
        "polyterm.cli.commands.whales",
        "polyterm.cli.commands.replay",
        "polyterm.cli.commands.portfolio",
        "polyterm.cli.commands.export_cmd",
        "polyterm.cli.commands.config_cmd",
    ]
    
    cli_ok = all(check_module(m) for m in cli_modules)
    
    # Check dependencies
    print("\nDependencies:")
    dependencies = [
        "click",
        "rich",
        "toml",
        "requests",
        "websockets",
        "aiohttp",
    ]
    
    deps_ok = all(check_module(m) for m in dependencies)
    
    # Check optional dependencies
    print("\nOptional Dependencies:")
    optional = [
        "plyer",
        "pandas",
        "pytest",
    ]
    
    for dep in optional:
        check_module(dep)
    
    # Summary
    print("\n" + "=" * 50)
    if core_ok and cli_ok:
        print("✓ PolyTerm core installation: OK")
    else:
        print("✗ PolyTerm core installation: FAILED")
    
    if deps_ok:
        print("✓ Dependencies: OK")
    else:
        print("✗ Dependencies: MISSING")
        print("\nInstall missing dependencies with:")
        print("  pip install -r requirements.txt")
    
    # Test CLI
    print("\n" + "=" * 50)
    print("Testing CLI...")
    try:
        from polyterm.cli.main import cli
        print("✓ CLI can be imported")
        
        # Try to get version
        from click.testing import CliRunner
        runner = CliRunner()
        result = runner.invoke(cli, ['--version'])
        if result.exit_code == 0:
            print(f"✓ CLI version: {result.output.strip()}")
        else:
            print(f"✗ CLI version check failed")
    except Exception as e:
        print(f"✗ CLI test failed: {e}")
    
    # Final status
    print("\n" + "=" * 50)
    if core_ok and cli_ok and deps_ok:
        print("✓ Installation verified successfully!")
        print("\nNext steps:")
        print("  1. Run 'polyterm --help' to see available commands")
        print("  2. Run 'polyterm config' to view/set configuration")
        print("  3. Run 'polyterm monitor' to start monitoring markets")
        return 0
    else:
        print("✗ Installation incomplete")
        print("\nPlease install missing dependencies and try again")
        return 1

if __name__ == "__main__":
    sys.exit(main())

