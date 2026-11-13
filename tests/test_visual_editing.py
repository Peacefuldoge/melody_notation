from pathlib import Path
import pytest
from melody_notation.core import parse_text, text_from_score, Score
from melody_notation.editing import update_note, add_slur, clear_slur, insert_note, delete_note
from melody_notation.png import render_score, export_png
from melody_notation.midi import export_midi, make_midi
from melody_notation.audio import export_audio


def base():
    return parse_text('title: 可视化测试\nkey: C\ntime: 4/4\nbpm: 120\nnotes:\n| 1 2 3 4 | 5 6 7 1\' |')


def test_update_degree_octave_duration_and_roundtrip():
    s=base()
    s=update_note(s,1,1,degree=6,octave=1,beats=.5)
    assert s.measures[0][0].midi_pitch('C')==81
    assert 'Measure 1' in ' '.join(s.validate())
    s=update_note(s,1,2,beats=1.5)
    assert s.validate()==[]
    out=text_from_score(s)
    assert "6'/2" in out
    assert '2.' in out
    assert parse_text(out).to_dict()==s.to_dict()


def test_slur_cross_measure_and_png(tmp_path):
    s=add_slur(base(),1,3,2,2)
    assert s.measures[0][2].slur_start
    assert s.measures[1][1].slur_end
    src=text_from_score(s)
    assert '(' in src and ')' in src
    loaded=parse_text(src)
    assert loaded.to_dict()==s.to_dict()
    assert len(render_score(s,bars_per_row=1)[1])==8
    path=export_png(s,tmp_path/'slur.png',bars_per_row=1)
    assert path.stat().st_size > 1000
    s2=clear_slur(s,2,1)
    assert not s2.measures[0][2].slur_start
    assert not s2.measures[1][1].slur_end
    assert s2.validate()==[]


def test_slur_rejects_overlap_and_rest():
    s=add_slur(base(),1,1,1,3)
    with pytest.raises(ValueError,match='overlaps'):
        add_slur(s,1,2,1,4)
    with pytest.raises(ValueError,match='Unclosed slur'):
        parse_text('title: X\nnotes: | ( 1 2 3 4 |')
    x=update_note(base(),1,2,degree=0)
    with pytest.raises(ValueError,match='rests'):
        add_slur(x,1,1,1,3)


def test_insert_delete_and_export(tmp_path):
    s=insert_note(base(),1,2,degree=0,beats=.5)
    assert s.validate()
    s=delete_note(s,1,2)
    assert s.validate()==[]
    s=add_slur(s,1,1,1,4)
    assert export_midi(s,tmp_path/'out.mid').exists()
    assert export_audio(s,tmp_path/'out.wav').exists()
    assert export_png(s,tmp_path/'out.png').exists()
    assert len(make_midi(s).instruments[0].notes)==8


def test_old_json_without_slur_flags_compatible():
    d=base().to_dict()
    for bar in d['measures']:
        for n in bar:
            n.pop('slur_start');n.pop('slur_end')
    s=Score.from_dict(d)
    assert not s.measures[0][0].slur_start


def test_slur_with_source_syntax():
    s=parse_text("title: X\nnotes:\n| ( 1 2 ) 3 4 |")
    assert s.measures[0][0].slur_start and s.measures[0][1].slur_end
    assert parse_text(text_from_score(s)).to_dict()==s.to_dict()
