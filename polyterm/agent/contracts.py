"""Stable JSON contracts for agent-facing PolyTerm tools."""

from datetime import datetime
from typing import Any, Dict, Optional

from ..utils.json_output import AGENT_SCHEMA_VERSION, make_envelope


def envelope(
    data: Any = None,
    *,
    meta: Optional[Dict[str, Any]] = None,
    schema_version: str = AGENT_SCHEMA_VERSION,
) -> Dict[str, Any]:
    """Return a successful agent response envelope."""
    merged_meta = {"generated_at": datetime.utcnow().isoformat() + "Z"}
    if meta:
        merged_meta.update(meta)
    return make_envelope(data=data, success=True, meta=merged_meta, schema_version=schema_version)


def error_envelope(
    message: str,
    *,
    data: Any = None,
    meta: Optional[Dict[str, Any]] = None,
    schema_version: str = AGENT_SCHEMA_VERSION,
) -> Dict[str, Any]:
    """Return a failed agent response envelope."""
    merged_meta = {"generated_at": datetime.utcnow().isoformat() + "Z"}
    if meta:
        merged_meta.update(meta)
    return make_envelope(
        data=data if data is not None else {},
        success=False,
        error=message,
        meta=merged_meta,
        schema_version=schema_version,
    )
