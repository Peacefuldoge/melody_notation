"""Tests MCP-exposed functions with a minimal MCPServer stub (no network/SDK needed)."""
import importlib
import sys
import types
from pathlib import Path
import pytest

@pytest.fixture
def server(monkeypatch,tmp_path):
    class FakeMCPServer:
        def __init__(self,*a,**kw): pass
        def tool(self):
            return lambda fn:fn
        def run(self,**kw):pass
    mcp_pkg=types.ModuleType('mcp')
    server_pkg=types.ModuleType('mcp.server')
    mcpserver_pkg=types.ModuleType('mcp.server.mcpserver')
    mcpserver_pkg.MCPServer=FakeMCPServer
    monkeypatch.setitem(sys.modules,'mcp',mcp_pkg)
    monkeypatch.setitem(sys.modules,'mcp.server',server_pkg)
    monkeypatch.setitem(sys.modules,'mcp.server.mcpserver',mcpserver_pkg)
    sys.modules.pop('melody_notation.mcp_server',None)
    m=importlib.import_module('melody_notation.mcp_server')
    m.ROOT=tmp_path.resolve()
    yield m
    sys.modules.pop('melody_notation.mcp_server',None)


def test_mcp_visual_tools_and_cross_bar_slur(server,tmp_path):
    s=server
    created=s.create_score('title: Test\nnotes:\n| 1 2 3 4 | 5 6 7 1\' |',overwrite=False)
    assert created['measures']==2
    with pytest.raises(ValueError,match='overwrite=true'):
        s.edit_note('score.jianpu',1,1,degree=5)
    result=s.edit_note('score.jianpu',1,1,degree=5,octave=1,overwrite=True)
    assert result['issues']==[]
    result=s.create_slur('score.jianpu',1,3,2,2,overwrite=True)
    assert result['issues']==[]
    assert '(' in (tmp_path/'score.jianpu').read_text()
    result=s.remove_slur('score.jianpu',2,1,overwrite=True)
    assert result['issues']==[]
    assert '(' not in (tmp_path/'score.jianpu').read_text()
    assert (tmp_path/'score.jianpu').is_file()


def test_mcp_invalid_intermediate_score_cannot_export(server):
    s=server
    s.create_score('title: X\nnotes: | 1 2 3 4 |')
    result=s.edit_note('score.jianpu',1,1,beats=.5,overwrite=True)
    assert result['issues']
    with pytest.raises(ValueError,match='Measure 1'):
        s.export_midi('score.jianpu','bad.mid')
    s.edit_note('score.jianpu',1,2,beats=1.5,overwrite=True)
    assert s.export_midi('score.jianpu','good.mid')


def test_mcp_path_escape_blocked(server):
    with pytest.raises(ValueError,match='inside'):
        server.inspect_score('../../important.txt')
