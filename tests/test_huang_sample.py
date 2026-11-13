from importlib import resources
from pathlib import Path
import pytest
from melody_notation.core import parse_text, text_from_score, timeline_events, Score
from melody_notation.gui import Editor
from melody_notation.midi import make_midi
from melody_notation.png import render_score


def test_old_samples_still_bundled():
    assert {'huang.jianpu','shanfeng.jianpu','visual_demo.jianpu','chiptune_ornaments.jianpu'} <= set(Editor.available_samples())


def test_huang_complete_visible_passages_and_key_change():
    txt=resources.files('melody_notation').joinpath('samples','huang.jianpu').read_text(encoding='utf8')
    score=parse_text(txt)
    assert score.title=='荒'
    assert score.bpm==88 and score.key=='A'
    assert score.key_changes == {25:'Bb'}
    assert len(score.measures)==41
    assert score.validate()==[]
    assert '歌词' not in text_from_score(score)
    assert parse_text(text_from_score(score)).to_dict()==score.to_dict()


def test_huang_modulation_works_with_midi_and_json():
    score=parse_text(resources.files('melody_notation').joinpath('samples','huang.jianpu').read_text(encoding='utf8'))
    events=list(timeline_events(score))
    # First note: low scale degree 6 in A = F#4 (midi 66)
    assert events[0][2]==66
    # Bar 25 begins with a rest and uses Bb; first sounding note is degree 1 in Bb = Bb4.
    first_after=sum(len(bar) for bar in score.measures[:24])
    # Excluding rests in timeline, verify local event via calculated position of 24 bars.
    bar25_time=24*4*60/score.bpm
    after=[e for e in events if e[0]>=bar25_time-1e-6]
    assert after[0][2]==70
    assert make_midi(score,'piano').instruments[0].notes
    assert Score.from_dict(score.to_dict()).to_dict()==score.to_dict()
    image,_=render_score(score, bars_per_row=3)
    assert image.width>=1440  # preserve exactly 3 bars per full row, widening if needed
