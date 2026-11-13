"""Regression cases for v0.5.1 quick keyboard transcription and dense engraving."""
from pathlib import Path

import pretty_midi

from melody_notation.core import blank_score_text, parse_text, text_from_score
from melody_notation.performance import PerformanceSession
from melody_notation.png import render_score, score_measure_layout


def blank():
    return parse_text(blank_score_text(), strict=False)


def notes(score):
    return [n for bar in score.measures for n in bar]


def test_fast_distinct_keystrokes_remain_distinct_and_roundtrip():
    session=PerformanceSession(blank())
    pitches=[60,62,64,65,67,69,71,72]
    for i,pitch in enumerate(pitches):
        t=100.0+i*.073
        session.note_on(pitch,90,now=t)
        session.note_off(pitch,now=t+.055)
    score=session.notation()
    score.validate(strict=True)
    sounding=[n for n in notes(score) if n.degree]
    assert [n.midi_pitch('C') for n in sounding]==pitches
    assert min(n.beats for n in sounding)==.125
    # The short gaps are ordinary key changes, not a string of rests.
    assert all(n.degree for n in notes(score)[:len(pitches)])
    assert parse_text(text_from_score(score),strict=True).measures


def test_actual_pause_is_still_rendered_as_rest():
    session=PerformanceSession(blank())
    session.note_on(60,now=2.0);session.note_off(60,now=2.12)
    session.note_on(62,now=2.9);session.note_off(62,now=3.1)
    ordered=notes(session.notation())
    first=next(i for i,n in enumerate(ordered) if n.degree==1)
    second=next(i for i,n in enumerate(ordered) if n.degree==2)
    assert any(n.degree==0 for n in ordered[first+1:second])


def test_fast_input_raw_midi_is_not_shifted_or_quantized(tmp_path):
    session=PerformanceSession(blank())
    session.note_on(60,81,now=10.0);session.note_off(60,now=10.027)
    session.note_on(62,109,now=10.076);session.note_off(62,now=10.119)
    session.notation()
    path=session.export_midi(tmp_path/'fast.mid')
    events=pretty_midi.PrettyMIDI(str(path)).instruments[0].notes
    assert [e.pitch for e in sorted(events,key=lambda e:e.start)]==[60,62]
    assert [e.velocity for e in sorted(events,key=lambda e:e.start)]==[81,109]
    assert abs(events[1].start-.076)<.01
    assert abs(events[0].end-.027)<.01


def test_dense_bar_keeps_requested_measure_count_and_nonoverlapping_hotspots():
    score=blank()
    from melody_notation.core import Note
    score.measures=[[Note((i % 7)+1, beats=.25) for i in range(16)],
                    [Note(1, beats=1) for _ in range(4)]]
    positions,rows,width=score_measure_layout(score,3,1200)
    assert rows==1
    assert positions[0][0]==0 and positions[1][0]==0
    assert width>1200
    im,hits=render_score(score,bars_per_row=3,width=1200)
    first=sorted((r[2][0],r[2][2]) for r in hits if r[0]==1)
    assert len(first)==16
    assert all(a[1] < b[0] for a,b in zip(first,first[1:]))
    assert im.height>300


def test_extreme_density_grows_page_instead_of_overlapping():
    from melody_notation.core import Note
    score=blank()
    score.measures=[[Note((i%7)+1,beats=.125) for i in range(32)]]
    positions,rows,width=score_measure_layout(score,3,1200)
    assert rows==1 and width>2000
    image,hits=render_score(score,width=1200)
    assert image.width==width
    spots=sorted((hit[2][0],hit[2][2]) for hit in hits)
    assert all(a[1]<b[0] for a,b in zip(spots,spots[1:]))
