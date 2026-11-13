from pathlib import Path
import pytest
from melody_notation.core import parse_text, timeline, text_from_score
from melody_notation.audio import synthesize, export_audio
from melody_notation.midi import make_midi, export_midi
from melody_notation.png import export_png

EXAMPLE = Path(__file__).parents[1] / 'examples/shanfeng.jianpu'

def test_parse_and_roundtrip():
    s=parse_text(EXAMPLE.read_text(encoding='utf-8'))
    assert len(s.measures)==4
    assert s.measures[1][0].beats==0.5
    assert s.measures[2][0].midi_pitch(s.key)==76
    assert parse_text(text_from_score(s)).to_dict()==s.to_dict()

def test_validation_catches_incomplete_bar():
    with pytest.raises(ValueError,match='Measure 1'):
        parse_text('title: X\nnotes: | 1 2 |')

def test_export(tmp_path):
    s=parse_text(EXAMPLE.read_text(encoding='utf-8'))
    assert len(make_midi(s,'flute').instruments[0].notes)==14
    assert synthesize(s,'piano').shape[0]>0
    assert export_midi(s,tmp_path/'x.mid','flute').stat().st_size>0
    assert export_audio(s,tmp_path/'x.wav','flute').stat().st_size>0
    assert export_png(s,tmp_path/'x.png').stat().st_size>0

def test_octaves_and_dots():
    s=parse_text("title: Test\nnotes: | 1' 5, 3. 6/2 |")
    assert sum(n.beats for n in s.measures[0])==4
    assert [n.midi_pitch('C') for n in s.measures[0]]==[72,55,64,69]
