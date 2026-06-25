"""Agent manifest and schema contract tests."""

import json
from pathlib import Path

from polyterm.agent.registry import get_cli_command_catalog, get_manifest, get_tools
from polyterm.agent.schemas import all_schemas
from polyterm.agent.mcp.server import TOOL_HANDLERS


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_all_manifest_tools_have_adapter_handlers():
    missing = [tool.name for tool in get_tools() if tool.adapter_available and tool.name not in TOOL_HANDLERS]
    assert missing == []


def test_static_manifest_matches_dynamic_manifest():
    static_manifest = json.loads((REPO_ROOT / "docs/tool-manifest.json").read_text())
    assert static_manifest == get_manifest()


def test_manifest_declares_protocol_and_json_lines_adapters():
    manifest = get_manifest()
    assert manifest["adapters"]["mcp"]["command"] == "polyterm agent mcp-server"
    assert manifest["adapters"]["mcp"]["optional_extra"] == "mcp"
    assert manifest["adapters"]["json_lines"]["command"] == "polyterm agent jsonl-server"
    assert manifest["adapters"]["mcp"]["tool_count"] == len(get_tools())
    assert manifest["adapters"]["json_lines"]["tool_count"] == len(get_tools())


def test_schema_artifacts_exist_for_every_tool():
    for tool in get_tools():
        schema_path = REPO_ROOT / tool.schema
        assert schema_path.exists(), tool.name
        schema = json.loads(schema_path.read_text())
        if "title" in schema:
            assert schema["title"] == f"PolyTerm {tool.name} response"
        assert "data" in schema["properties"]


def test_generated_schema_keys_match_tools():
    assert sorted(all_schemas()) == sorted(tool.name for tool in get_tools())


def test_mutating_tools_require_confirmation():
    mutating = [tool for tool in get_tools() if tool.mutates_local_state]
    assert mutating
    assert all(tool.requires_confirmation for tool in mutating)


def test_cli_catalog_includes_lazy_commands_and_update():
    catalog = get_cli_command_catalog()
    names = {row["name"] for row in catalog}
    assert "agent" in names
    assert "search" in names
    assert "update" in names
    assert len(catalog) >= 84
