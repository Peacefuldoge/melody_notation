"""Regression tests for v0.5.2 sidebar collapse and live keyboard tone."""
from __future__ import annotations

import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')

import numpy as np
import pytest

from melody_notation.layout_ops import navigation_split_sizes
from melody_notation.live_audio import LiveAudioSynth
from melody_notation.midi import INSTRUMENTS


def test_splitter_collapse_gives_every_spare_pixel_to_editor():
    assert navigation_split_sizes([310, 930, 290],54) == [54,1186,290]
    assert navigation_split_sizes([54,1186,290],310) == [310,930,290]
    assert navigation_split_sizes([310,1210,0],54) == [54,1466,0]
    with pytest.raises(ValueError):
        navigation_split_sizes([20,50],54)


def _live_wave(tone):
    synth=LiveAudioSynth()
    synth.instrument=tone
    synth._ensure_stream=lambda:True  # no output hardware involved
    assert synth.note_on('keyboard',60)
    assert synth._voices['keyboard',60]['instrument']==tone
    audio=np.zeros((2048,2),dtype=np.float32)
    synth._render(audio,len(audio),None,None)
    assert np.isfinite(audio).all()
    assert np.max(abs(audio)) > 0.01
    return audio[:,0]


def test_every_keyboard_instrument_can_render_and_preserves_note_on_timbre():
    for name in INSTRUMENTS:
        samples=_live_wave(name)
        assert samples.size==2048
    assert not np.allclose(_live_wave('gameboy'),_live_wave('flute'))
    assert not np.allclose(_live_wave('clarinet'),_live_wave('piano'))
    synth=LiveAudioSynth()
    synth._ensure_stream=lambda:True
    synth.instrument='flute'
    synth.note_on('keyboard',60)
    synth.instrument='gameboy'
    assert synth._voices['keyboard',60]['instrument']=='flute'


def test_real_gui_sidebar_and_keyboard_instrument(monkeypatch):
    pytest.importorskip('PySide6')
    from PySide6.QtWidgets import QApplication
    from melody_notation.qt_gui import MelodyMainWindow
    from melody_notation.core import parse_text, blank_score_text
    from melody_notation.qt_gui import ScoreEditor
    app=QApplication.instance() or QApplication([])
    # No system audio device or OS MIDI port is needed for this test.
    monkeypatch.setattr('melody_notation.qt_piano.MidiInputRouter.set_active',lambda *a:None)
    score=ScoreEditor(parse_text(blank_score_text(),strict=False))
    audio=score._live_audio
    monkeypatch.setattr(audio,'note_on',lambda *a,**k:True)
    monkeypatch.setattr(audio,'note_off',lambda *a,**k:None)
    score.keyboard_panel.keyboard_instrument.setCurrentText('flute')
    assert score.live_instrument=='flute'
    assert audio.instrument=='flute'
    assert score.keyboard_panel.keyboard_instrument.count()==len(INSTRUMENTS)
    score.close()
    # Avoid opening demo folders; construct the window with no recent projects.
    monkeypatch.setattr('melody_notation.qt_gui.load_recent_projects',lambda:[])
    monkeypatch.setattr(MelodyMainWindow,'open_sample',lambda self:None)
    main=MelodyMainWindow()
    main.show();app.processEvents()
    assert main.sidebar.isVisible()
    main.toggle_sidebar();app.processEvents()
    assert not main.sidebar.isVisible()
    assert main.nav_shell.width()==main.rail.width()
    assert main.sides.sizes()[1]>main.sides.sizes()[0]
    main.toggle_sidebar();app.processEvents()
    assert main.sidebar.isVisible()
    assert main.nav_shell.width()>=260
    main.close()
