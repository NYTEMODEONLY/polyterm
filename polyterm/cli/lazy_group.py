"""Helpers for lazy CLI command loading."""

import ast
from importlib import import_module
from pathlib import Path

import click
from click.utils import make_default_short_help


LAZY_COMMANDS = {
    "monitor": ("monitor", "monitor"),
    "watch": ("watch", "watch"),
    "whales": ("whales", "whales"),
    "replay": ("replay", "replay"),
    "portfolio": ("portfolio", "portfolio"),
    "export": ("export_cmd", "export"),
    "config": ("config_cmd", "config"),
    "live-monitor": ("live_monitor", "live_monitor"),
    "arbitrage": ("arbitrage", "arbitrage"),
    "predict": ("predict", "predict"),
    "orderbook": ("orderbook", "orderbook"),
    "wallets": ("wallets", "wallets"),
    "alerts": ("alerts", "alerts"),
    "tutorial": ("tutorial", "tutorial"),
    "glossary": ("glossary", "glossary"),
    "simulate": ("simulate", "simulate"),
    "risk": ("risk", "risk"),
    "follow": ("follow", "follow"),
    "parlay": ("parlay", "parlay"),
    "bookmarks": ("bookmarks", "bookmarks"),
    "dashboard": ("dashboard", "dashboard"),
    "chart": ("chart", "chart"),
    "size": ("size", "size"),
    "compare": ("compare", "compare"),
    "recent": ("recent", "recent"),
    "pricealert": ("pricealert", "pricealert"),
    "calendar": ("calendar", "calendar"),
    "fees": ("fees", "fees"),
    "stats": ("stats", "stats"),
    "search": ("search", "search"),
    "position": ("position", "position"),
    "notes": ("notes", "notes"),
    "presets": ("presets", "presets"),
    "sentiment": ("sentiment", "sentiment"),
    "correlate": ("correlate", "correlate"),
    "exit": ("exit", "exit"),
    "depth": ("depth", "depth"),
    "trade": ("trade", "trade"),
    "timeline": ("timeline", "timeline"),
    "analyze": ("analytics", "analyze"),
    "journal": ("journal", "journal"),
    "hot": ("hot", "hot"),
    "lookup": ("lookup", "lookup"),
    "pnl": ("pnl", "pnl"),
    "center": ("alertcenter", "center"),
    "groups": ("groups", "groups"),
    "attribution": ("attribution", "attribution"),
    "snapshot": ("snapshot", "snapshot"),
    "signals": ("signals", "signals"),
    "similar": ("similar", "similar"),
    "ladder": ("ladder", "ladder"),
    "benchmark": ("benchmark", "benchmark"),
    "pin": ("pin", "pin"),
    "spread": ("spread", "spread"),
    "history": ("history", "history"),
    "streak": ("streak", "streak"),
    "digest": ("digest", "digest"),
    "timing": ("timing", "timing"),
    "odds": ("odds", "odds"),
    "health": ("health", "health"),
    "scenario": ("scenario", "scenario"),
    "summary": ("summary", "summary"),
    "watchdog": ("watchdog", "watchdog"),
    "volume": ("volume", "volume"),
    "screener": ("screener", "screener"),
    "backtest": ("backtest", "backtest"),
    "report": ("report", "report"),
    "liquidity": ("liquidity", "liquidity"),
    "ev": ("ev", "ev"),
    "calibrate": ("calibrate", "calibrate"),
    "quick": ("quick", "quick"),
    "leaderboard": ("leaderboard", "leaderboard"),
    "notify": ("notify", "notify"),
    "crypto15m": ("crypto15m", "crypto15m"),
    "mywallet": ("mywallet", "mywallet"),
    "quicktrade": ("quicktrade", "quicktrade"),
    "negrisk": ("negrisk", "negrisk"),
    "rewards": ("rewards", "rewards"),
    "clusters": ("clusters", "clusters"),
    "news": ("news", "news"),
}


class LazyGroup(click.Group):
    """Click group that loads subcommands only when requested."""

    def __init__(self, *args, lazy_commands=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.lazy_commands = dict(lazy_commands or {})
        self.lazy_help = {}

    def list_commands(self, ctx):
        command_names = set(super().list_commands(ctx))
        command_names.update(self.lazy_commands)
        return sorted(command_names)

    def get_command(self, ctx, cmd_name):
        command = self.commands.get(cmd_name)
        if command is not None:
            return command

        spec = self.lazy_commands.get(cmd_name)
        if spec is None:
            return None

        module_name, attr_name = spec
        module = import_module(f"{__package__}.commands.{module_name}")
        command = getattr(module, attr_name)
        self.add_command(command, cmd_name)
        return command

    def format_commands(self, ctx, formatter):
        rows = []
        for command_name in self.list_commands(ctx):
            command = self.commands.get(command_name)
            if command is not None and command.hidden:
                continue

            help_text = self._get_short_help(command_name, formatter.width - 6)
            rows.append((command_name, help_text))

        if rows:
            with formatter.section("Commands"):
                formatter.write_dl(rows)

    def _get_short_help(self, cmd_name, limit):
        command = self.commands.get(cmd_name)
        if command is not None:
            return command.get_short_help_str(limit)

        help_text = self._get_lazy_help_text(cmd_name)
        if not help_text:
            return ""
        return make_default_short_help(help_text, limit)

    def _get_lazy_help_text(self, cmd_name):
        if cmd_name in self.lazy_help:
            return self.lazy_help[cmd_name]

        spec = self.lazy_commands.get(cmd_name)
        if spec is None:
            return ""

        module_name, attr_name = spec
        module_path = Path(__file__).with_name("commands") / f"{module_name}.py"

        try:
            module_ast = ast.parse(module_path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            help_text = ""
        else:
            help_text = ""
            for node in module_ast.body:
                if isinstance(node, ast.FunctionDef) and node.name == attr_name:
                    help_text = ast.get_docstring(node) or ""
                    break

        self.lazy_help[cmd_name] = help_text
        return help_text
