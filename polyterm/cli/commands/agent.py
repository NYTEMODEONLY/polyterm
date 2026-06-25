"""Agent command - manifests, schemas, and MCP server entrypoints"""

import json

import click
from rich.console import Console
from rich.table import Table

from ...agent.contracts import envelope
from ...agent.doctor import AgentDoctor
from ...agent.mcp.fastmcp_server import main as run_fastmcp_server
from ...agent.mcp.server import main as run_jsonl_server
from ...agent.registry import get_cli_command_catalog, get_manifest
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


@agent.command()
@click.option("--format", "output_format", type=click.Choice(["json"]), default="json")
def catalog(output_format):
    """Print the full PolyTerm CLI command catalog for agents."""
    print_json(envelope(get_cli_command_catalog(), meta={"tool": "agent.catalog"}))


@agent.command()
@click.option("--skip-network", is_flag=True, help="Skip live Data API and CLOB connectivity checks.")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
def doctor(skip_network, output_format):
    """Diagnose PolyTerm agent and MCP installation health."""
    result = AgentDoctor().run(skip_network=skip_network, check_mcp=True)
    if output_format == "json":
        print_json(envelope(result, meta={"tool": "agent.doctor"}))
        return

    console = Console()
    table = Table(title="PolyTerm Agent Doctor")
    table.add_column("Check")
    table.add_column("Status", justify="center")
    table.add_column("Message")
    for check in result["checks"]:
        table.add_row(check["name"], check["status"].upper(), check["message"])
    console.print(table)
    console.print(f"[dim]Summary: {result['summary']['status']}[/dim]")


@agent.command("mcp-server")
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse", "streamable-http"]),
    default="stdio",
    show_default=True,
    help="MCP transport to serve.",
)
@click.option("--mount-path", default=None, help="Mount path for HTTP transports.")
def mcp_server(transport, mount_path):
    """Run the real FastMCP protocol server."""
    raise SystemExit(run_fastmcp_server(transport=transport, mount_path=mount_path))


@agent.command("jsonl-server")
def jsonl_server():
    """Run the legacy JSON-lines stdio adapter."""
    raise SystemExit(run_jsonl_server())


@agent.command()
def examples():
    """Print example JSON-lines and MCP usage requests."""
    examples_payload = {
        "mcp_server": {
            "command": "polyterm",
            "args": ["agent", "mcp-server"],
            "hermes_config": {
                "mcp_servers": {
                    "polyterm": {
                        "command": "polyterm",
                        "args": ["agent", "mcp-server"],
                        "timeout": 120,
                        "connect_timeout": 60,
                    }
                }
            },
        },
        "legacy_jsonl": [
            {"method": "manifest"},
            {"tool": "market.search", "args": {"query": "bitcoin", "limit": 3}},
            {"tool": "analytics.thesis", "args": {"market": "bitcoin"}},
            {"tool": "wallet.inspect", "args": {"address": "0x..."}},
        ],
    }
    click.echo(json.dumps(examples_payload, indent=2))
