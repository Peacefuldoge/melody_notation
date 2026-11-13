"""Regression: v4 arrangement opening and v5 legato synth/async spinner."""
from pathlib import Path
import ast
import numpy as np
import soundfile as sf
from melody_notation.audio import _tone, synthesize, SAMPLE_RATE
from melody_notation.core import parse_text
from melody_notation.arrangement import Arrangement
from melody_notation.preview_engine import render_preview

ROOT = Path(__file__).resolve().parents[1]


def _rms(audio):
    return float(np.sqrt(np.mean(np.square(audio.astype(np.float64)))))


def test_arrangement_timeline_grid_has_four_beat_bar_size_before_use():
    # The v4 crash was a missing local `major` used on the first paint event.
    tree=ast.parse((ROOT/'src/qt_gui.py').read_text(encoding='utf-8'))
    track=next(node for node in tree.body if isinstance(node,ast.ClassDef) and node.name=='TrackEditor')
    paint=next(node for node in ast.walk(track) if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef))
               and 'major' in [n.id for n in ast.walk(node) if isinstance(n,ast.Name)
                               and isinstance(n.ctx,ast.Load)])
    stores=[n for n in ast.walk(paint) if isinstance(n,ast.Name) and n.id=='major'
            and isinstance(n.ctx,ast.Store)]
    reads=[n for n in ast.walk(paint) if isinstance(n,ast.Name) and n.id=='major'
           and isinstance(n.ctx,ast.Load)]
    assert stores and reads
    assert stores[0].lineno < min(r.lineno for r in reads)
    demo=ROOT/'demo_projects'/'我的第一份工程'/'主题编排.mtrack'
    assert len(Arrangement.load(demo).tracks)>=2


def test_piano_guitar_and_music_box_notes_have_audible_body_and_release():
    for instrument in ('piano','guitar','music_box','flute','violin'):
        note=_tone(60,.5,instrument,SAMPLE_RATE)
        assert .55 < len(note)/SAMPLE_RATE < .9
        assert np.isfinite(note).all()
        assert _rms(note[int(.3*SAMPLE_RATE):int(.4*SAMPLE_RATE)]) > .007, instrument
        assert _rms(note[int(.52*SAMPLE_RATE):int(.58*SAMPLE_RATE)]) > .002, instrument
        assert abs(float(note[-1])) < .002


def test_adjacent_notes_overlap_smoothly_without_changing_score_timing(tmp_path):
    score=parse_text('title: Legato\nkey: C\ntime: 4/4\nbpm: 120\nnotes:\n| 1 2 3 4 |')
    mix=synthesize(score,'piano')
    # A quarter note at 120 BPM lasts 0.5 s; its predecessor continues
    # to sound during the next note's attack, unlike the previous 70 ms decay.
    assert _rms(mix[int(.25*SAMPLE_RATE):int(.4*SAMPLE_RATE)]) > .015
    assert _rms(mix[int(.52*SAMPLE_RATE):int(.56*SAMPLE_RATE)]) > .01
    assert len(mix)==int((2.+.45)*SAMPLE_RATE)
    output=tmp_path/'normal.wav'
    render_preview('jianpu',score,None,'piano',1.,output)
    wave,sr=sf.read(output)
    assert sr==SAMPLE_RATE
    assert _rms(wave[int(.3*SAMPLE_RATE):int(.4*SAMPLE_RATE)]) > .015


def test_spinner_is_wired_to_async_state_and_stop():
    source=(ROOT/'src/qt_gui.py').read_text(encoding='utf-8')
    assert 'self._spinner_timer.timeout.connect(self._spin_preview_icon)' in source
    assert 'self._set_rendering(True)' in source
    assert 'self._set_rendering(False)' in source
    assert 'synthesis_spinner_icon(self.theme,self._spinner_phase)' in source
    assert 'if self._rendering:return' in source
