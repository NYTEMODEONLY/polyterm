"""Agent command - manifests, schemas, and MCP-ready server"""

import json

import click

from ...agent.contracts import envelope
from ...agent.mcp.server import main as run_mcp_server
from ...agent.registry import get_manifest
from ...agent.schemas import all_schemas, schema_for_tool
from ...utils.json_output import print_json


@click.group()
def agent():
    """Expose PolyTerm's agent-safe tool surface"""


@agent.command()
@click.option("--format", "output_format", type=click.Choice(["json"]), default="json")
def manifest(output_format):
    """Print the machine-readable agent tool manifest"""
    print_json(envelope(get_manifest(), meta={"tool": "agent.manifest"}))


@agent.command()
@click.argument("tool", required=False)
@click.option("--format", "output_format", type=click.Choice(["json"]), default="json")
def schemas(tool, output_format):
    """Print JSON Schemas for one tool or every tool"""
    payload = schema_for_tool(tool) if tool else all_schemas()
    print_json(envelope(payload, meta={"tool": "agent.schemas"}))


@agent.command("mcp-server")
def mcp_server():
    """Run the MCP-ready JSON-lines stdio adapter"""
    raise SystemExit(run_mcp_server())


@agent.command()
def examples():
    """Print example JSON-lines requests for the MCP-ready adapter"""
    examples_payload = [
        {"method": "manifest"},
        {"tool": "market.search", "args": {"query": "bitcoin", "limit": 3}},
        {"tool": "analytics.thesis", "args": {"market": "bitcoin"}},
        {"tool": "wallet.inspect", "args": {"address": "0x..."}},
    ]
    click.echo(json.dumps(examples_payload, indent=2))
