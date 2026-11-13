"""Regression tests for v0.2.4 ornament semantics, speed and chiptune."""
from dataclasses import asdict
import numpy as np
import pytest
from melody_notation.core import Score, parse_text, text_from_score, timeline, timeline_events
from melody_notation.editing import update_note
from melody_notation.midi import INSTRUMENTS, make_midi
from melody_notation.png import export_png
from melody_notation.audio import synthesize, export_audio, SAMPLE_RATE

SOURCE = """title: 八比特练习
key: C
time: 4/4
bpm: 120
notes:
| 1{tr} 2{mordent} 3{turn} 5{staccato} |
| 6{accent} 5{tenuto} 3{lower_mordent} 1{tremolo} |
"""


def test_ornaments_roundtrip_and_legacy_json():
    s=parse_text(SOURCE)
    assert s.validate()==[]
    assert [n.ornament for n in s.measures[0]] == ['tr','mordent','turn','staccato']
    assert parse_text(text_from_score(s)).to_dict()==s.to_dict()
    assert Score.from_dict(s.to_dict()).to_dict() == s.to_dict()
    d=s.to_dict()
    for bar in d['measures']:
        for note in bar: note.pop('ornament')
    old=Score.from_dict(d)
    assert not old.measures[0][0].ornament


def test_ornaments_not_allowed_on_rest_or_invalid():
    for token in ('0{tr}', '1{invalid}', '2{TR}'):
        with pytest.raises(ValueError): parse_text('title: X\nnotes:\n| '+token+' 2 3 4 |')
    s=parse_text(SOURCE)
    with pytest.raises(ValueError,match='Rest'):
        update_note(s,1,1,degree=0,ornament='tr')


def test_ornament_edit_clear_and_validation():
    s=parse_text('title: X\nnotes:\n| 1 2 3 4 |')
    s=update_note(s,1,2,ornament='tr')
    assert '{tr}' in text_from_score(s)
    assert s.validate()==[]
    s=update_note(s,1,2,ornament='')
    assert '{tr}' not in text_from_score(s)
    assert s.validate()==[]


def test_trill_diatonic_upper_neighbor_and_length():
    s=parse_text(SOURCE)
    events=list(timeline_events(s))
    assert events[0][2]==60  # C4
    assert events[1][2]==62  # D4 in major key
    assert events[0][0]==0
    assert events[-1][1] <= 4.0
    # Ornaments subdivide, but do not move measure starts
    assert events[8][0] < 1.0
    assert sum(n.beats for bar in s.measures for n in bar)==8


def test_midi_velocity_articulation():
    s=parse_text(SOURCE)
    pm=make_midi(s,'gameboy')
    notes=pm.instruments[0].notes
    assert INSTRUMENTS['gameboy']==80
    assert len(notes)>8
    assert max(n.velocity for n in notes)==116
    assert len([n for n in notes if n.pitch==60])>=2


def test_faster_playback_shorter_without_higher_pitch():
    s=parse_text(SOURCE)
    slow=list(timeline_events(s,1.0))
    for factor in (1.25,1.5,1.75,2):
        fast=list(timeline_events(s,factor))
        assert [n[2] for n in fast]==[n[2] for n in slow]
        assert fast[0][0]==0
        assert fast[-1][1]==pytest.approx(slow[-1][1]/factor)
        audio=synthesize(s,'gameboy',speed=factor)
        # v0.4.3 preview synth keeps a 0.45 s tail for ambience/reverb.
        assert len(audio)==int((8*.5/factor+.45)*SAMPLE_RATE)
        assert np.isfinite(audio).all() and np.max(abs(audio))>0.01
    assert len(synthesize(s,'piano',speed=2))<len(synthesize(s,'piano',speed=1))


def test_ornament_export_wav_midi_png(tmp_path):
    s=parse_text(SOURCE)
    assert export_png(s,tmp_path/'orn.png').stat().st_size > 1000
    assert export_audio(s,tmp_path/'gameboy.wav','gameboy').stat().st_size > 1000
    assert len(make_midi(s).instruments[0].notes)>8


def test_speed_invalid():
    s=parse_text(SOURCE)
    for rate in (0, -1, 5):
        with pytest.raises(ValueError): synthesize(s,'piano',speed=rate)
