"""Exercise MCP tool bodies without requiring optional network-installed SDK."""
import sys
import types
import importlib
from pathlib import Path
import pytest
from melody_notation.workspace import ProjectWorkspace

SCORE='title: Song\nkey: C\ntime: 4/4\nbpm: 120\nnotes:\n| 1 2 3 4 |'


def test_mcp_multitrack_actions(tmp_path, monkeypatch):
    fake=types.ModuleType('mcp')
    server=types.ModuleType('mcp.server')
    modern=types.ModuleType('mcp.server.mcpserver')
    class FakeMCPServer:
        def __init__(self,*args,**kwargs):pass
        def tool(self):return lambda func:func
    modern.MCPServer=FakeMCPServer
    monkeypatch.setitem(sys.modules,'mcp',fake)
    monkeypatch.setitem(sys.modules,'mcp.server',server)
    monkeypatch.setitem(sys.modules,'mcp.server.mcpserver',modern)
    # Avoid leaking this fake server module into other tests.
    sys.modules.pop('melody_notation.mcp_server',None)
    from melody_notation import mcp_server as m
    project=ProjectWorkspace.create(tmp_path,'MCP project')
    m.ROOT=project.root
    project.new_score('melody.jianpu',SCORE)
    assert 'gameboy' in m.list_drum_kits()['kits']
    d=m.create_drum_pattern('beat.drum',title='节奏',kit='gameboy')
    assert d['kit']=='gameboy'
    assert m.inspect_drum_pattern('beat.drum')['hits']['kick'] == []
    with pytest.raises(ValueError):m.toggle_drum_hit('beat.drum','kick',0)
    t=m.toggle_drum_hit('beat.drum','kick',0,overwrite=True)
    assert t['active'] is True
    out=m.create_arrangement('session.mtrack','演示')
    assert out['tracks']==0
    with pytest.raises(ValueError):m.add_arrangement_clip('session.mtrack','melody.jianpu')
    c=m.add_arrangement_clip('session.mtrack','melody.jianpu',overwrite=True)
    assert c['track_index']==0
    m.add_arrangement_clip('session.mtrack','beat.drum',overwrite=True)
    with pytest.raises(ValueError):m.edit_arrangement_clip('session.mtrack',0,0,reversed=True)
    changed=m.edit_arrangement_clip('session.mtrack',0,0,
                      reversed=True,trim_start=1,trim_end=3,overwrite=True)
    assert changed['clip']['reversed'] is True
    info=m.inspect_arrangement('session.mtrack')
    assert len(info['arrangement']['tracks'])==2
    moved=m.reorder_arrangement_track('session.mtrack',0,1,overwrite=True)
    assert moved['new_index']==1
    result=m.export_multitrack_midi('session.mtrack','mix.mid')
    assert Path(result).stat().st_size>100
    output=m.export_multitrack_audio('session.mtrack','mix.wav')
    assert Path(output).stat().st_size>1000
    output=m.export_drum_pattern('beat.drum','beat.mid')
    assert Path(output).stat().st_size>50  # One inserted kick is still valid MIDI.
    import pretty_midi
    assert [n.pitch for i in pretty_midi.PrettyMIDI(str(output)).instruments for n in i.notes] == [36]
    with pytest.raises(ValueError):m.add_arrangement_clip('session.mtrack','../elsewhere.jianpu',overwrite=True)
    sys.modules.pop('melody_notation.mcp_server',None)
