"""Agent adapter handler tests."""

from polyterm.agent.mcp import server


def test_manifest_request_returns_envelope():
    payload = server.handle_request({"method": "manifest"})
    assert payload["success"] is True
    assert payload["schema_version"]
    assert payload["data"]["name"] == "polyterm"
    assert payload["data"]["tools"]


def test_unknown_tool_returns_failed_envelope():
    payload = server.handle_request({"tool": "missing.tool"})
    assert payload["success"] is False
    assert "Unknown tool" in payload["error"]


def test_every_registered_handler_returns_envelope(monkeypatch):
    def fake_handler(**kwargs):
        return {
            "schema_version": "test",
            "success": True,
            "data": {"ok": True, "args": kwargs},
            "error": None,
            "meta": {},
        }

    monkeypatch.setattr(server, "TOOL_HANDLERS", {name: fake_handler for name in server.TOOL_HANDLERS})

    for name in server.TOOL_HANDLERS:
        payload = server.handle_request({"tool": name, "args": {"sample": "value"}})
        assert payload["success"] is True
        assert payload["data"]["args"] == {"sample": "value"}


def test_mutating_alert_tool_requires_confirmation(monkeypatch):
    class FakeEngine:
        def __init__(self, *args, **kwargs):
            pass

        def create_price_rule(self, **kwargs):
            return {"created": False, "dry_run": True, "rule": kwargs}

    from polyterm.agent.mcp.tools import alerts

    monkeypatch.setattr(alerts, "AlertEngine", FakeEngine)
    payload = alerts.create_price_rule(market="bitcoin", above=0.8, dry_run=False, confirm=False)
    assert payload["success"] is False
    assert "mutates local SQLite state" in payload["error"]
    assert payload["data"]["dry_run"] is True
