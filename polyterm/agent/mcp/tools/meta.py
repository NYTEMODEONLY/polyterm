"""Agent meta tools for adapter dispatch."""

from ...contracts import envelope, error_envelope
from ...doctor import AgentDoctor
from ...schemas import all_schemas, schema_for_tool


def schemas(tool: str = "") -> dict:
    try:
        payload = schema_for_tool(tool) if tool else all_schemas()
        return envelope(payload, meta={"tool": "agent.schemas"})
    except KeyError as exc:
        return error_envelope(str(exc), meta={"tool": "agent.schemas"})


def doctor(skip_network: bool = False, check_mcp: bool = True) -> dict:
    return envelope(
        AgentDoctor().run(skip_network=skip_network, check_mcp=check_mcp),
        meta={"tool": "agent.doctor"},
    )
