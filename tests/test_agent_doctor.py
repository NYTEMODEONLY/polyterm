"""Tests for agent doctor diagnostics."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

from click.testing import CliRunner

from polyterm.agent.doctor import AgentDoctor
from polyterm.cli.main import cli


class FakeDB:
    def get_database_stats(self):
        return {"markets": 1, "research_briefs": 2}


class FakeDataAPI:
    def get_recent_trades(self, limit=1):
        return [{"id": "trade"}]

    def close(self):
        pass


class FakeCLOB:
    def get_current_markets(self, limit=1):
        return [{"id": "market"}]

    def close(self):
        pass


def test_agent_doctor_reports_local_health_with_network_skipped():
    doctor = AgentDoctor(database_factory=lambda: FakeDB())

    result = doctor.run(skip_network=True, check_mcp=False)

    checks = {check["name"]: check for check in result["checks"]}
    assert result["summary"]["status"] == "ok"
    assert checks["schema_files"]["status"] == "ok"
    assert checks["manifest_sync"]["status"] == "ok"
    assert checks["sqlite_archive"]["details"]["tables"]["research_briefs"] == 2
    assert checks["data_api_connectivity"]["status"] == "skipped"
    assert checks["clob_api_connectivity"]["status"] == "skipped"
    assert result["hermes_config"]["mcp_servers"]["polyterm"]["args"] == ["agent", "mcp-server"]


def test_agent_doctor_checks_network_factories():
    doctor = AgentDoctor(
        data_api_factory=lambda: FakeDataAPI(),
        clob_factory=lambda: FakeCLOB(),
        database_factory=lambda: FakeDB(),
    )

    result = doctor.run(check_mcp=False)

    checks = {check["name"]: check for check in result["checks"]}
    assert checks["data_api_connectivity"]["status"] == "ok"
    assert checks["data_api_connectivity"]["details"]["rows"] == 1
    assert checks["clob_api_connectivity"]["status"] == "ok"
    assert checks["clob_api_connectivity"]["details"]["rows"] == 1


def test_agent_doctor_detects_manifest_drift(tmp_path):
    repo = tmp_path
    docs = repo / "docs"
    docs.mkdir()
    (docs / "tool-manifest.json").write_text(json.dumps({"tools": []}), encoding="utf-8")
    schema_dir = docs / "schemas"
    schema_dir.mkdir()
    for tool in AgentDoctor().run(skip_network=True, check_mcp=False)["checks"]:
        assert tool["status"] in {"ok", "skipped"}

    doctor = AgentDoctor(repo_root=repo, database_factory=lambda: FakeDB())
    result = doctor.run(skip_network=True, check_mcp=False)

    checks = {check["name"]: check for check in result["checks"]}
    assert checks["manifest_sync"]["status"] == "error"
    assert checks["manifest_sync"]["details"]["missing_static"]
    assert result["summary"]["status"] == "error"


@patch("polyterm.cli.commands.agent.AgentDoctor")
def test_agent_doctor_cli_returns_stable_json(mock_doctor_cls, tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    mock_doctor = Mock()
    mock_doctor.run.return_value = {
        "summary": {"status": "ok"},
        "checks": [],
        "hermes_config": {},
        "quality_flags": ["agent_doctor"],
    }
    mock_doctor_cls.return_value = mock_doctor

    runner = CliRunner()
    result = runner.invoke(cli, ["agent", "doctor", "--skip-network", "--format", "json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["schema_version"] == "2026-06-25"
    assert payload["success"] is True
    assert payload["data"]["summary"]["status"] == "ok"
    assert payload["meta"]["tool"] == "agent.doctor"
    mock_doctor.run.assert_called_once_with(skip_network=True, check_mcp=True)
