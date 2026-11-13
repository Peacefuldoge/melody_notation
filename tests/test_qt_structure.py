"""Qt GUI integration is optional during core-only / CI runs."""
import pytest

PySide6=pytest.importorskip('PySide6')
from PySide6.QtWidgets import QApplication
from melody_notation.qt_gui import ScoreEditor, DrumEditor, TrackEditor
from melody_notation.core import parse_text
from melody_notation.drums import default_drum_pattern
from melody_notation.arrangement import Arrangement


def test_three_document_widget_types():
    app=QApplication.instance() or QApplication([])
    score=ScoreEditor(parse_text('title: Test\nkey: C\ntime: 4/4\nbpm: 120\nnotes:\n| 1 2 3 4 |'))
    drum=DrumEditor(default_drum_pattern())
    track=TrackEditor(Arrangement(),'demo.mtrack')
    score._choose_note(1,1)
    assert score.selected_note==(1,1)
    drum.toggle(0,1)
    assert 1 in drum.pattern.hits['kick']
    assert track.arrangement.tracks==[]
    score.close();drum.close();track.close()
