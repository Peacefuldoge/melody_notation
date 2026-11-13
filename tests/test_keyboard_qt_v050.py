"""GUI smoke tests for v0.5.0 (run automatically when PySide6 is available)."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')

import pytest
pytest.importorskip('PySide6')
from PySide6.QtWidgets import QApplication
from melody_notation.core import parse_text, blank_score_text
from melody_notation.qt_gui import ScoreEditor, DrumEditor
from melody_notation.qt_piano import PianoKeys

@pytest.fixture(scope='module')
def app():
    instance=QApplication.instance() or QApplication([])
    yield instance


def test_piano_is_below_score_source_and_can_collapse(app):
    widget=ScoreEditor(parse_text(blank_score_text(),strict=False))
    box=widget.layout()
    assert box.indexOf(widget.source_panel)<box.indexOf(widget.keyboard_panel)
    assert box.indexOf(widget.keyboard_panel)==box.count()-1
    assert widget.keyboard_panel.contents.isVisibleTo(widget.keyboard_panel)
    widget.keyboard_panel.toggle.setChecked(False)
    assert not widget.keyboard_panel.contents.isVisibleTo(widget.keyboard_panel)
    widget.keyboard_panel.toggle.setChecked(True)
    assert widget.keyboard_panel.contents.isVisibleTo(widget.keyboard_panel)
    widget.set_theme('olive')
    assert widget.keyboard_panel.piano.theme=='olive'
    widget.set_input_active(False)
    widget.deleteLater()


def test_recording_creates_editable_score_and_one_undo_step(app,monkeypatch):
    w=ScoreEditor(parse_text(blank_score_text(),strict=False))
    monkeypatch.setattr(w._live_audio,'note_on',lambda *args,**kw:True)
    monkeypatch.setattr(w._live_audio,'note_off',lambda *args,**kw:None)
    w.keyboard_panel.record.setChecked(True)
    assert w.source.isReadOnly()
    w.perform_note_on(60,96,'keyboard')
    assert w.score.measures[0][0].degree==1
    w.perform_note_off(60,'keyboard')
    w.keyboard_panel.record.setChecked(False)
    assert not w.source.isReadOnly()
    assert len(w.history)==1
    w.undo()
    assert w.score.measures==[[]]
    w.set_input_active(False)
    w.deleteLater()


def test_piano_theme_colors_and_score_only_widget(app):
    piano=PianoKeys()
    colors=[]
    for theme in ('light','dark','olive','beige'):
        piano.set_theme(theme)
        colors.append(piano._color())
    assert len(set(colors))==4
    assert 'KeyboardPanel' not in type(DrumEditor).__name__
