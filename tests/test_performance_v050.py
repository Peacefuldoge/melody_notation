"""Live keyboard/MIDI capture and score conversion (headless, device-free)."""
from __future__ import annotations

from pathlib import Path
import pretty_midi
import pytest

from melody_notation.core import blank_score_text, parse_text, text_from_score
from melody_notation.performance import (
    DEFAULT_KEYS, PerformanceSession, pitch_to_note,
    validate_mapping, normalized_key)


def new_session():
    ticks=[100.0]
    session=PerformanceSession(parse_text(blank_score_text(),strict=False),clock=lambda: ticks[0])
    return session,ticks


def test_default_keymap_has_distinct_pitches():
    assert validate_mapping(DEFAULT_KEYS)==DEFAULT_KEYS
    assert DEFAULT_KEYS['A']==60 and DEFAULT_KEYS['K']==72
    assert normalized_key('a')=='A'
    with pytest.raises(ValueError):normalized_key('Ctrl+A')
    with pytest.raises(ValueError):validate_mapping({'A':60,'B':60})


@pytest.mark.parametrize('pitch', list(range(48,85)))
def test_pitch_to_degree_exact_midi(pitch):
    n=pitch_to_note(pitch,'C',beats=.5)
    assert n.midi_pitch('C')==pitch
    assert n.beats==.5


def test_real_time_transcription_including_provisional_and_rest():
    session,t=new_session()
    assert session.note_on(60,90,now=100.)
    live=session.notation(now=100.03)
    assert live.measures[0][0].degree==1
    session.note_off(60,now=100.51)  # 1 beat
    session.note_on(64,80,now=101.01)  # 2-beat position
    session.note_off(64,now=101.25)   # half beat
    score=session.notation()
    score.validate(strict=True)
    assert score.measures[0][0].degree==1
    assert any(n.degree==0 for n in score.measures[0])
    assert any(n.degree==3 for n in score.measures[0])
    assert parse_text(text_from_score(score),strict=True).measures


def test_holding_notes_over_bar_boundary_and_backwards_compatible_text():
    session,_=new_session()
    session.note_on(72,100,now=100.)
    session.note_off(72,now=104.25)  # 8.5 beats
    score=session.notation()
    assert len(score.measures)==3
    assert score.measures[0][0].midi_pitch('C')==72
    roundtrip=parse_text(text_from_score(score),strict=True)
    assert [[(n.degree,n.octave,n.accidental,n.beats) for n in bar] for bar in roundtrip.measures] == [[(n.degree,n.octave,n.accidental,n.beats) for n in bar] for bar in score.measures]


def test_keep_existing_music_when_recording_new_material():
    base=parse_text('title: Example\nkey: C\ntime: 4/4\nbpm: 120\nnotes:\n| 1 2 3 4 |',strict=True)
    s=PerformanceSession(base,clock=lambda: 100.)
    s.note_on(67,100,now=100.)
    s.note_off(67,now=100.5)
    new=s.notation()
    assert new.measures[0]==base.measures[0]
    assert len(new.measures)==2
    new.validate(strict=True)


def test_chords_preserved_in_midi_even_if_score_monophonic(tmp_path):
    session,_=new_session()
    session.note_on(60,85,now=100.0)
    session.note_on(64,101,now=100.0)
    session.note_on(67,112,now=100.0)
    for pitch in (60,64,67):session.note_off(pitch,now=100.65)
    score=session.notation()
    score.validate(strict=True)
    assert {n.degree for bar in score.measures for n in bar if n.degree}=={1}
    output=session.export_midi(tmp_path/'chord.mid')
    pm=pretty_midi.PrettyMIDI(str(output))
    assert len(pm.instruments[0].notes)==3
    assert sorted(n.pitch for n in pm.instruments[0].notes)==[60,64,67]
    assert sorted(n.velocity for n in pm.instruments[0].notes)==[85,101,112]


def test_recorded_rest_and_octave_shift_with_accidental():
    session,_=new_session()
    session.note_on(61,90,now=100.25)
    session.note_off(61,now=100.5)
    score=session.notation()
    assert any(n.degree==0 for n in score.measures[0])
    assert any(n.accidental for n in score.measures[0])
    score.validate(strict=True)


def test_finish_closes_held_key_and_midi_can_export(tmp_path):
    session,_=new_session()
    session.note_on(62,100,now=100.)
    session.finish(now=100.4)
    assert not session.active
    assert len(session.notes)==1
    assert session.export_midi(tmp_path/'one.mid').exists()


def test_legato_second_onset_is_not_lost_by_first_held_note():
    session,_=new_session()
    session.note_on(60,90,now=100.0)
    session.note_on(62,90,now=100.30)
    session.note_off(60,now=100.65)
    session.note_off(62,now=100.90)
    degrees=[n.degree for bar in session.notation().measures for n in bar if n.degree]
    assert degrees[:2]==[1,2]


def test_record_starts_timing_at_first_note_not_record_click():
    session,ticks=new_session()
    assert session.origin is None
    ticks[0]=135.0  # user waited 35 seconds after clicking Record
    session.note_on(60,90,now=135.)
    session.note_off(60,now=135.48)
    score=session.notation()
    assert len(score.measures)==1
    assert score.measures[0][0].degree==1
    assert not any(n.degree==0 for n in score.measures[0][:1])


def test_appended_take_respects_existing_key_change():
    base=parse_text('title: Modulation\nkey: C\ntime: 4/4\nbpm: 120\nkey_changes: 2=Bb\nnotes:\n| 1 2 3 4 | 1 2 3 4 |',strict=True)
    take=PerformanceSession(base,clock=lambda:100.)
    take.note_on(70,100,now=100.)  # Bb4 = degree 1 after Bb modulation
    take.note_off(70,now=100.5)
    result=take.notation()
    note=result.measures[2][0]
    assert note.degree==1
    assert note.midi_pitch('Bb')==70
