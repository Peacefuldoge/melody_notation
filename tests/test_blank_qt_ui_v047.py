"""Optional Windows Qt smoke: a blank document can receive its first note."""
import os
import pytest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
pytest.importorskip('PySide6')
from PySide6.QtWidgets import QApplication
from melody_notation.qt_gui import ScoreEditor, DrumEditor
from melody_notation.core import blank_score_text, parse_text
from melody_notation.drums import default_drum_pattern


def test_blank_score_and_drum_editor_smoke():
    app = QApplication.instance() or QApplication([])
    editor = ScoreEditor(parse_text(blank_score_text()))
    assert editor.score.measures == [[]]
    assert editor.selected_note is None
    editor.insert_after()
    assert len(editor.score.measures[0]) == 1
    assert editor.selected_note == (1, 1)
    editor.undo()
    assert editor.score.measures == [[]]
    drum = DrumEditor(default_drum_pattern())
    assert drum.table.rowCount() == 3
    assert all(not hits for hits in drum.pattern.hits.values())
    assert all(drum.table.item(r, c).text().strip() == '' for r in range(3) for c in range(32))
    editor.close()
    drum.close()
