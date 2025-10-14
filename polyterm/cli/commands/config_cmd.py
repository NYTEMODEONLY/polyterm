"""Config command - manage configuration"""

import click
from rich.console import Console
from rich.table import Table

from ...utils.config import Config


@click.command(name="config")
@click.option("--set", "set_value", nargs=2, multiple=True, help="Set config value (key value)")
@click.option("--get", "get_key", help="Get config value")
@click.option("--list", "list_all", is_flag=True, help="List all configuration")
@click.option("--reset", is_flag=True, help="Reset to default configuration")
@click.pass_context
def config(ctx, set_value, get_key, list_all, reset):
    """Manage PolyTerm configuration"""
    
    cfg = ctx.obj["config"]
    console = Console()
    
    if reset:
        # Reset to defaults
        cfg.config = cfg.DEFAULT_CONFIG.copy()
        cfg.save()
        console.print("[green]Configuration reset to defaults[/green]")
        return
    
    if set_value:
        # Set values
        for key, value in set_value:
            # Try to parse as number or boolean
            if value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False
            else:
                try:
                    value = float(value)
                    if value.is_integer():
                        value = int(value)
                except ValueError:
                    pass  # Keep as string
            
            cfg.set(key, value)
            console.print(f"[green]Set {key} = {value}[/green]")
        
        cfg.save()
        console.print(f"\n[cyan]Configuration saved to:[/cyan] {cfg.config_path}")
        return
    
    if get_key:
        # Get single value
        value = cfg.get(get_key)
        if value is not None:
            console.print(f"{get_key} = {value}")
        else:
            console.print(f"[yellow]Key not found: {get_key}[/yellow]")
        return
    
    if list_all:
        # List all configuration
        console.print(f"[bold]Configuration:[/bold] {cfg.config_path}\n")
        
        def print_dict(d, indent=0):
            for key, value in d.items():
                if isinstance(value, dict):
                    console.print("  " * indent + f"[cyan]{key}:[/cyan]")
                    print_dict(value, indent + 1)
                else:
                    console.print("  " * indent + f"[cyan]{key}:[/cyan] {value}")
        
        print_dict(cfg.config)
        return
    
    # Default: show common settings
    table = Table(title="PolyTerm Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="yellow")
    
    table.add_row("Config Path", str(cfg.config_path))
    table.add_row("", "")
    table.add_row("[bold]Alerts[/bold]", "")
    table.add_row("  Probability Threshold", f"{cfg.probability_threshold}%")
    table.add_row("  Volume Threshold", f"{cfg.volume_threshold}%")
    table.add_row("  Check Interval", f"{cfg.check_interval}s")
    table.add_row("", "")
    table.add_row("[bold]API[/bold]", "")
    table.add_row("  Gamma Base URL", cfg.gamma_base_url)
    table.add_row("  CLOB Endpoint", cfg.clob_endpoint)
    table.add_row("  Subgraph Endpoint", cfg.subgraph_endpoint[:50] + "...")
    table.add_row("", "")
    table.add_row("[bold]Wallet[/bold]", "")
    table.add_row("  Address", cfg.wallet_address or "[dim]Not set[/dim]")
    
    console.print(table)
    console.print(f"\n[dim]Use 'polyterm config --list' for full configuration[/dim]")
    console.print(f"[dim]Use 'polyterm config --set key value' to update settings[/dim]")

