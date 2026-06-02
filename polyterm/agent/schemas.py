"""JSON Schema helpers for PolyTerm agent tools."""

from typing import Any, Dict

from .registry import get_tools


BASE_ENVELOPE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["schema_version", "success", "data", "error", "meta"],
    "properties": {
        "schema_version": {"type": "string"},
        "success": {"type": "boolean"},
        "data": {"type": ["object", "array", "string", "number", "boolean", "null"]},
        "error": {"type": ["string", "null"]},
        "meta": {"type": "object"},
    },
}


def schema_for_tool(tool_name: str) -> Dict[str, Any]:
    """Return a lightweight output schema for one tool."""
    tools = {tool.name: tool for tool in get_tools()}
    if tool_name not in tools:
        raise KeyError(f"Unknown agent tool: {tool_name}")

    schema = dict(BASE_ENVELOPE_SCHEMA)
    schema["title"] = f"PolyTerm {tool_name} response"
    schema["description"] = tools[tool_name].description
    return schema


def all_schemas() -> Dict[str, Dict[str, Any]]:
    """Return schemas keyed by tool name."""
    return {tool.name: schema_for_tool(tool.name) for tool in get_tools()}


def validate_envelope(payload: Dict[str, Any]) -> bool:
    """Minimal validation for generated agent envelopes."""
    required = {"schema_version", "success", "data", "error", "meta"}
    return isinstance(payload, dict) and required.issubset(payload.keys())
