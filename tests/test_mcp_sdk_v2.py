"""MCP SDK v2-only import/registration contract checks.

Uses an SDK-shaped fake; real SDK 2.x handshake is verified separately on a
machine with the optional MCP dependency installed.
"""
from __future__ import annotations

import importlib
from pathlib import Path
import sys
import types

import pytest


@pytest.fixture
def fake_sdk(monkeypatch):
    class StubMCPServer:
        def __init__(self, name, *, instructions):
            self.name = name
            self.instructions = instructions
            self.tools = []

        def tool(self):
            def register(function):
                self.tools.append(function.__name__)
                return function
            return register

        def run(self, *, transport):
            assert transport == "stdio"

    mcp_pkg = types.ModuleType("mcp")
    server_pkg = types.ModuleType("mcp.server")
    modern = types.ModuleType("mcp.server.mcpserver")
    modern.MCPServer = StubMCPServer
    monkeypatch.setitem(sys.modules, "mcp", mcp_pkg)
    monkeypatch.setitem(sys.modules, "mcp.server", server_pkg)
    monkeypatch.setitem(sys.modules, "mcp.server.mcpserver", modern)
    monkeypatch.delitem(sys.modules, "mcp.server.fastmcp", raising=False)
    sys.modules.pop("melody_notation.mcp_server", None)
    try:
        yield
    finally:
        sys.modules.pop("melody_notation.mcp_server", None)


def test_sdk_v2_tools_register_and_start(fake_sdk, tmp_path: Path):
    service = importlib.import_module("melody_notation.mcp_server")
    assert service.mcp.name == "Melody Notation"
    assert len(service.mcp.tools) == 31
    assert {"list_instruments", "create_score", "create_drum_pattern", "create_arrangement"} <= set(service.mcp.tools)
    service.ROOT = tmp_path
    result = service.create_drum_pattern("empty.drum")
    assert Path(result["path"]).exists()
    service.main()


def test_sdk_legacy_only_is_not_supported(monkeypatch):
    """Installing only v1 must fail rather than silently run a legacy server."""
    legacy_pkg = types.ModuleType("mcp")
    server_pkg = types.ModuleType("mcp.server")
    legacy = types.ModuleType("mcp.server.fastmcp")
    legacy.FastMCP = object
    monkeypatch.setitem(sys.modules, "mcp", legacy_pkg)
    monkeypatch.setitem(sys.modules, "mcp.server", server_pkg)
    monkeypatch.setitem(sys.modules, "mcp.server.fastmcp", legacy)
    monkeypatch.delitem(sys.modules, "mcp.server.mcpserver", raising=False)
    sys.modules.pop("melody_notation.mcp_server", None)
    try:
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module("melody_notation.mcp_server")
    finally:
        sys.modules.pop("melody_notation.mcp_server", None)


def test_mcp_dependency_only_allows_v2():
    tomllib = pytest.importorskip("tomllib")
    data = tomllib.loads((Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8"))
    for extra in ("mcp", "all"):
        requirements = [dep for dep in data["project"]["optional-dependencies"][extra] if dep.startswith("mcp")]
        assert requirements == ["mcp>=2,<3"]
    assert data["project"]["version"] == "0.5.10"
