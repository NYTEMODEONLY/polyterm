"""Tests for GitHub-only install source helpers."""

from unittest.mock import Mock

from polyterm.utils.install_source import (
    GITHUB_PIPX_SPEC,
    PIPX_FORCE_INSTALL_CMD,
    manual_reinstall_commands,
    pip_upgrade_from_github_cmd,
    reinstall_from_github,
)


def test_pipx_force_install_uses_github_git_spec_not_pypi_package_name():
    assert PIPX_FORCE_INSTALL_CMD == (
        "pipx",
        "install",
        "--force",
        GITHUB_PIPX_SPEC,
    )
    assert GITHUB_PIPX_SPEC.startswith("git+https://")
    assert PIPX_FORCE_INSTALL_CMD[3] != "polyterm"


def test_pip_upgrade_uses_github_git_spec_not_pypi_package_name():
    cmd = pip_upgrade_from_github_cmd("/usr/bin/python")
    assert cmd[-1] == GITHUB_PIPX_SPEC
    assert "polyterm" not in cmd[3:-1]


def test_manual_reinstall_commands_never_recommend_pypi_package_name():
    pipx_cmd, pip_cmd = manual_reinstall_commands()
    assert "git+https://github.com/NYTEMODEONLY/polyterm.git@main" in pipx_cmd
    assert "git+https://github.com/NYTEMODEONLY/polyterm.git@main" in pip_cmd
    assert "pipx install polyterm" not in pipx_cmd
    assert "pip install --upgrade polyterm" not in pip_cmd
    assert "pipx upgrade polyterm" not in pipx_cmd


def test_reinstall_prefers_pipx_from_github():
    runner = Mock()
    runner.side_effect = [
        Mock(returncode=0),  # pipx --version
        Mock(returncode=0, stdout="ok", stderr=""),  # pipx install --force git+...
    ]

    ok, method, error = reinstall_from_github("python", runner=runner)

    assert ok is True
    assert method == "pipx"
    assert error == ""
    install_call = runner.call_args_list[1][0][0]
    assert install_call == list(PIPX_FORCE_INSTALL_CMD)


def test_reinstall_falls_back_to_pip_from_github_when_pipx_missing():
    runner = Mock()

    def _run(cmd, **kwargs):
        if cmd[:2] == ["pipx", "--version"]:
            raise FileNotFoundError("pipx")
        if cmd[:4] == ["python", "-m", "pip", "--version"]:
            return Mock(returncode=0)
        if cmd[-1] == GITHUB_PIPX_SPEC and "-m" in cmd:
            return Mock(returncode=0, stdout="ok", stderr="")
        raise AssertionError(f"unexpected command: {cmd}")

    runner.side_effect = _run

    ok, method, error = reinstall_from_github("python", runner=runner)

    assert ok is True
    assert method == "pip"
    assert error == ""


def test_reinstall_reports_missing_installers():
    runner = Mock(side_effect=FileNotFoundError("missing"))

    ok, method, error = reinstall_from_github("python", runner=runner)

    assert ok is False
    assert method == ""
    assert "Neither pipx nor pip" in error


def test_reinstall_never_invokes_bare_pypi_package_name():
    runner = Mock()
    runner.side_effect = [
        Mock(returncode=0),
        Mock(returncode=1, stdout="", stderr="failed"),
        Mock(returncode=0),
        Mock(returncode=1, stdout="", stderr="failed"),
    ]

    reinstall_from_github("python", runner=runner)

    for call in runner.call_args_list:
        cmd = call[0][0]
        assert cmd != ["pipx", "install", "polyterm"]
        assert cmd != ["pipx", "upgrade", "polyterm"]
        assert cmd != ["python", "-m", "pip", "install", "--upgrade", "polyterm"]
        if "install" in cmd or "upgrade" in cmd:
            joined = " ".join(cmd)
            if "polyterm" in joined:
                assert GITHUB_PIPX_SPEC in joined
