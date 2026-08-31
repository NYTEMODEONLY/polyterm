"""GitHub is the install source of truth. PyPI is decommissioned."""

from __future__ import annotations

import subprocess
from typing import Callable, Optional, Sequence

GITHUB_REPO_URL = "https://github.com/NYTEMODEONLY/polyterm.git"
GITHUB_PIPX_SPEC = "git+https://github.com/NYTEMODEONLY/polyterm.git@main"

PIPX_FORCE_INSTALL_CMD = ("pipx", "install", "--force", GITHUB_PIPX_SPEC)

CommandRunner = Callable[..., subprocess.CompletedProcess]


def pip_upgrade_from_github_cmd(python_executable: str) -> tuple[str, ...]:
    """Return the pip command that reinstalls from GitHub main."""
    return (python_executable, "-m", "pip", "install", "--upgrade", GITHUB_PIPX_SPEC)


def manual_reinstall_commands() -> tuple[str, str]:
    """User-facing reinstall commands. Never the PyPI package name."""
    return (
        f"pipx install --force {GITHUB_PIPX_SPEC}",
        f"pip install --upgrade {GITHUB_PIPX_SPEC}",
    )


def _run(
    runner: CommandRunner,
    cmd: Sequence[str],
    *,
    check: bool = False,
) -> Optional[subprocess.CompletedProcess]:
    try:
        return runner(list(cmd), capture_output=True, text=True, check=check)
    except FileNotFoundError:
        return None
    except subprocess.CalledProcessError:
        return None


def reinstall_from_github(
    python_executable: str,
    *,
    runner: Optional[CommandRunner] = None,
) -> tuple[bool, str, str]:
    """Reinstall PolyTerm from GitHub main via pipx, then pip.

    Does not query PyPI and never installs the bare ``polyterm`` package name.

    Returns:
        ``(success, method, error_text)`` where method is ``pipx``, ``pip``,
        or empty when neither installer is available.
    """
    if runner is None:
        runner = subprocess.run
    pipx_probe = _run(runner, ("pipx", "--version"), check=True)
    if pipx_probe is not None:
        result = _run(runner, PIPX_FORCE_INSTALL_CMD)
        if result is not None and result.returncode == 0:
            return True, "pipx", ""
        pipx_error = "" if result is None else (result.stderr or result.stdout or "")
    else:
        pipx_error = ""

    pip_cmd = pip_upgrade_from_github_cmd(python_executable)
    pip_probe = _run(runner, (python_executable, "-m", "pip", "--version"), check=True)
    if pip_probe is None:
        return False, "", pipx_error or "Neither pipx nor pip could be found."

    result = _run(runner, pip_cmd)
    if result is not None and result.returncode == 0:
        return True, "pip", ""
    pip_error = "" if result is None else (result.stderr or result.stdout or "")
    return False, "pip", pip_error or pipx_error
