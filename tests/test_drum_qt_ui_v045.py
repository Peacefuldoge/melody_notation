"""Optional GUI check: add, rename, delete and undo rows in Qt."""
import pytest
pytest.importorskip('PySide6')
from PySide6.QtWidgets import QApplication
from melody_notation.qt_gui import DrumEditor
from melody_notation.drums import default_drum_pattern


def test_manage_rows_qt():
    app=QApplication.instance() or QApplication([])
    w=DrumEditor(default_drum_pattern())
    assert w.table.rowCount()==3
    w.add_track()
    assert w.table.rowCount()==4
    assert w.table.verticalHeaderItem(3).text()=='新建鼓点 4'
    w._change_track_sound('track_4','hihat')
    assert w.pattern.tracks[3].sound=='hihat'
    w.remove_track('track_4')
    assert w.table.rowCount()==3
    w.undo()
    assert w.table.rowCount()==4
    w.redo()
    assert w.table.rowCount()==3
    w.close()
