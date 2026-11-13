"""Validate harmony references and read-only MCP retrieval without a live model."""
from __future__ import annotations
import importlib
import json
from pathlib import Path
import sys
import types
import pytest
from melody_notation.harmony import TOPICS, read_topic

PROJECT = Path(__file__).resolve().parents[1]


def _pitch_class(note: str) -> int:
    base = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
    assert note[0] in base
    modifier = note[1:].replace('♭','b').replace('♯','#')
    assert set(modifier) <= {'b','#'}
    return (base[note[0]] + modifier.count('#') - modifier.count('b')) % 12


def test_catalog_chord_intervals_and_spellings():
    data = json.loads((PROJECT/'src/harmony/chords.json').read_text(encoding='utf-8'))
    chords = data['chords']
    assert len(chords) >= 25
    assert len({c['type'] for c in chords}) == len(chords)
    for c in chords:
        notes, semitones = c['notes_C'], c['semitones_from_root']
        assert len(notes) == len(semitones), c['type']
        assert 0 in semitones
        assert all(isinstance(x,int) and 0 <= x <= 24 for x in semitones)
        assert [_pitch_class(n) for n in notes] == [s%12 for s in semitones], c['type']
        assert c['mood_tendency_zh'] and c['typical_use_zh']
    d={c['type']:c['semitones_from_root'] for c in chords}
    assert d['maj7']==[0,4,7,11]
    assert d['7']==[0,4,7,10]
    assert d['add9']==[0,4,7,14]
    assert d['9']==[0,4,7,10,14]
    assert d['sus4']==[0,5,7]
    assert d['m7b5']==[0,3,6,10]
    assert d['dim7']==[0,3,6,9]


def test_skill_is_discoverable_and_reference_copies_match():
    skill=PROJECT/'.agents/skills/melody-harmony'
    readme=(skill/'SKILL.md').read_text(encoding='utf-8')
    assert readme.startswith('---\nname: melody-harmony\ndescription:')
    assert '$melody-harmony' in readme
    assert '多轨' in readme
    assert readme == (PROJECT/'skills/melody-harmony/SKILL.md').read_text(encoding='utf-8')
    for ref in ('chords.md','progressions.md','workflow.md','sources.md','chords.json'):
        canonical=(PROJECT/'src/harmony'/ref).read_bytes()
        assert canonical==(skill/'references'/ref).read_bytes()
        assert canonical==(PROJECT/'skills/melody-harmony/references'/ref).read_bytes()
    assert 'melody-harmony' in (PROJECT/'AGENTS.md').read_text(encoding='utf-8')


def test_harmony_topic_reader_rejects_unknown_and_has_all_topics():
    assert set(TOPICS)=={'overview','chords','progressions','workflow','sources'}
    for topic in TOPICS:
        assert len(read_topic(topic))>120
    for topic in ('../secrets', '/etc/passwd', 'invalid', 'chords.md'):
        with pytest.raises(ValueError, match='Unknown harmony topic'):
            read_topic(topic)


def test_mcp_readonly_harmony_tools(monkeypatch,tmp_path):
    class FakeMCPServer:
        def __init__(self,*a,**kwargs): pass
        def tool(self): return lambda fn: fn
    m=types.ModuleType('mcp')
    ms=types.ModuleType('mcp.server')
    modern=types.ModuleType('mcp.server.mcpserver')
    modern.MCPServer=FakeMCPServer
    monkeypatch.setitem(sys.modules, 'mcp',m)
    monkeypatch.setitem(sys.modules, 'mcp.server',ms)
    monkeypatch.setitem(sys.modules, 'mcp.server.mcpserver',modern)
    sys.modules.pop('melody_notation.mcp_server',None)
    try:
        server=importlib.import_module('melody_notation.mcp_server')
        server.ROOT=tmp_path.resolve()
        before=list(tmp_path.iterdir())
        topics=server.list_harmony_topics()
        assert 'chords' in topics and 'workflow' in topics
        for topic in topics:
            result=server.read_harmony_guide(topic)
            assert result['topic']==topic and result['content']==read_topic(topic)
        assert list(tmp_path.iterdir()) == before  # no score writes
        with pytest.raises(ValueError):
            server.read_harmony_guide('../secret')
    finally:
        sys.modules.pop('melody_notation.mcp_server',None)
