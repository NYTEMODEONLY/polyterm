"""Tests for PolyTerm's agent schema surface."""

import pytest

from polyterm.agent.schemas import all_schemas, schema_for_tool


def test_schema_for_tool_exposes_agent_usable_input_output_and_safety_metadata():
    schema = schema_for_tool("wallet.whales")

    assert schema["tool"] == "wallet.whales"
    assert schema["description"] == "Return wallet-level whale activity and smart-money candidates."
    assert schema["command"] == "polyterm whales --wallets --format json"
    assert schema["schema_path"] == "docs/schemas/wallet.whales.schema.json"

    assert schema["safety"] == {
        "read_only": True,
        "mutates_local_state": False,
        "requires_confirmation": False,
        "may_prompt": False,
        "long_running": False,
    }

    input_schema = schema["input_schema"]
    assert input_schema["type"] == "object"
    assert input_schema["additionalProperties"] is False
    assert input_schema["properties"] == {
        "min_notional": {"type": "number"},
        "hours": {"type": "integer"},
        "limit": {"type": "integer"},
    }
    assert input_schema["required"] == []

    output_schema = schema["output_schema"]
    assert output_schema["required"] == ["schema_version", "success", "data", "error", "meta"]
    assert output_schema["properties"]["success"] == {"type": "boolean"}


def test_schema_for_tool_infers_required_args_from_command_placeholders():
    schema = schema_for_tool("market.search")

    assert schema["input_schema"]["properties"] == {
        "query": {"type": "string"},
        "limit": {"type": "integer"},
    }
    assert schema["input_schema"]["required"] == ["query"]


def test_all_schemas_returns_rich_schema_for_every_registered_tool():
    schemas = all_schemas()

    assert "agent.schemas" in schemas
    assert "market.research" in schemas
    assert "analytics.thesis" in schemas
    assert schemas["market.research"]["input_schema"]["required"] == ["market"]
    assert "input_schema" in schemas["analytics.thesis"]
    assert "output_schema" in schemas["analytics.thesis"]
    assert "safety" in schemas["alerts.create_price_rule"]
    assert schemas["alerts.create_price_rule"]["safety"]["mutates_local_state"] is True


def test_schema_for_tool_rejects_unknown_tool():
    with pytest.raises(KeyError):
        schema_for_tool("missing.tool")
