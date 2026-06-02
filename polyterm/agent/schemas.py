"""JSON Schema helpers for PolyTerm agent tools."""

import copy
import json
import re
from pathlib import Path
from typing import Any, Dict, List

from .registry import AgentTool, get_tools


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
    """Return an agent-usable schema packet for one tool."""
    tools = {tool.name: tool for tool in get_tools()}
    if tool_name not in tools:
        raise KeyError(f"Unknown agent tool: {tool_name}")

    tool = tools[tool_name]
    output_schema = _output_schema(tool)

    return {
        "tool": tool.name,
        "description": tool.description,
        "command": tool.command,
        "schema_path": tool.schema,
        "safety": {
            "read_only": tool.read_only,
            "mutates_local_state": tool.mutates_local_state,
            "requires_confirmation": tool.requires_confirmation,
            "may_prompt": tool.may_prompt,
            "long_running": tool.long_running,
        },
        "input_schema": _input_schema(tool),
        "output_schema": output_schema,
    }


def all_schemas() -> Dict[str, Dict[str, Any]]:
    """Return schemas keyed by tool name."""
    return {tool.name: schema_for_tool(tool.name) for tool in get_tools()}


def _input_schema(tool: AgentTool) -> Dict[str, Any]:
    """Build a JSON Schema object for one tool's arguments."""
    return {
        "type": "object",
        "properties": {name: _json_type(arg_type) for name, arg_type in tool.args.items()},
        "required": _required_args(tool),
        "additionalProperties": False,
    }


def _output_schema(tool: AgentTool) -> Dict[str, Any]:
    """Load a documented output schema when present, otherwise use the generic envelope."""
    schema_path = Path(__file__).resolve().parents[2] / tool.schema
    if schema_path.exists():
        with schema_path.open("r", encoding="utf-8") as handle:
            output_schema = json.load(handle)
    else:
        output_schema = copy.deepcopy(BASE_ENVELOPE_SCHEMA)
    output_schema.setdefault("title", f"PolyTerm {tool.name} response")
    output_schema.setdefault("description", tool.description)
    return output_schema


def _json_type(arg_type: Any) -> Dict[str, Any]:
    """Convert registry argument shorthand into JSON Schema primitive declarations."""
    kind = str(arg_type).lower()
    if kind in {"string", "integer", "number", "boolean"}:
        return {"type": kind}
    if kind == "array":
        return {"type": "array", "items": {"type": "string"}}
    return {"type": "string"}


def _required_args(tool: AgentTool) -> List[str]:
    """Infer required args from command placeholders such as ``{query}``."""
    placeholders = re.findall(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", tool.command)
    return [name for name in tool.args if name in placeholders]


def validate_envelope(payload: Dict[str, Any]) -> bool:
    """Minimal validation for generated agent envelopes."""
    required = {"schema_version", "success", "data", "error", "meta"}
    return isinstance(payload, dict) and required.issubset(payload.keys())
