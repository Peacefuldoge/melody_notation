"""Optional GUI smoke tests, run on Windows with pip install -e '.[gui,test]'"""
import os
from pathlib import Path
import pytest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
pytest.importorskip('PySide6')
from PySide6.QtWidgets import QApplication, QTableWidget
from melody_notation.arrangement import Arrangement
from melody_notation.qt_gui import TrackEditor, ArrangementTimeline


def test_daw_layout_selection_drag_undo_and_split():
    app=QApplication.instance() or QApplication([])
    root=Path(__file__).resolve().parents[1]
    path=root/'demo_projects'/'我的第一份工程'/'主题编排.mtrack'
    editor=TrackEditor(Arrangement.load(path),path)
    assert isinstance(editor.timeline,ArrangementTimeline)
    assert not editor.findChildren(QTableWidget)  # the old empty tables are gone
    assert len(editor.arrangement.tracks)==3
    editor.select_clip(0,0)
    assert editor.current_clip().source=='山风.jianpu'
    editor.timeline_change(0,0,'move',2.21,0)
    assert editor.current_clip().start_beat==2.25
    editor.undo()
    assert editor.arrangement.tracks[0].clips[0].start_beat==0
    editor.select_clip(0,0)
    editor.split_selected(8)
    assert len(editor.arrangement.tracks[0].clips)==2
    editor.undo()
    assert len(editor.arrangement.tracks[0].clips)==1
    editor.close()
