"""v0.5.7: adaptive performance toolbar regression tests."""
from __future__ import annotations

import os
import pytest
from melody_notation.piano_layout import toolbar_row_groups


@pytest.mark.parametrize('width,expected_count', [
    (1450, 1), (950, 2), (650, 2), (420, 4),
])
def test_wrap_atomic_groups_instead_of_clipping(width, expected_count):
    # Representative widths for Windows controls at 100% display scaling.
    sizes = (103, 209, 170, 254, 151, 192)
    rows = toolbar_row_groups(width, sizes)
    assert len(rows) == expected_count
    assert tuple(i for row in rows for i in row) == tuple(range(len(sizes)))
    assert rows[-1][-1] == len(sizes)-1  # octave controls remain the last group
    for row in rows:
        assert sum(sizes[i] for i in row) + 8*(len(row)-1) <= width


def test_wrap_boundary_and_empty_toolbar():
    assert toolbar_row_groups(100, ()) == ()
    assert toolbar_row_groups(80, (80, 90, 70)) == ((0,), (1,), (2,))
    assert toolbar_row_groups(100, (47, 45), spacing=8) == ((0, 1),)
    assert toolbar_row_groups(99, (47, 45), spacing=8) == ((0,), (1,))


def test_qt_toolbar_is_one_surface_without_overlaps_or_unwanted_scroll(monkeypatch):
    pytest.importorskip('PySide6')
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    from PySide6.QtWidgets import QApplication
    from melody_notation.qt_gui import ScoreEditor
    from melody_notation.core import blank_score_text, parse_text
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr('melody_notation.qt_piano.MidiInputRouter.set_active', lambda *_: None)
    editor = ScoreEditor(parse_text(blank_score_text(), strict=False))
    editor.show()
    app.processEvents()
    try:
        panel = editor.keyboard_panel
        bar = panel.toolbar
        assert not hasattr(panel, 'toolbar_scroll')
        assert len(bar._sections) == 3
        assert bar.minimumSizeHint().width() == 0
        assert panel.scroller.minimumWidth() == 0
        for width in (1450, 850, 600, 420, 1450):
            editor.resize(width+24, 880)
            app.processEvents()
            assert len(bar._sections) == 3
            assert 1 <= bar.row_count <= 3
            rects = [part.geometry() for part in bar._sections]
            for i, rect in enumerate(rects):
                assert rect.left() >= 0
                assert rect.right() <= bar.width()
                assert rect.bottom() <= bar.height()
                for other in rects[i+1:]:
                    assert not rect.intersects(other), (width, rect, other)
            assert rects[-1].right() <= bar.width()
        panel.set_start_octave(3, persist=False)
        assert panel.piano.LOW == 48
        assert panel.octave_range.text().startswith('C')
        panel.octave_up.click()
        assert panel.piano.LOW == 60
    finally:
        editor.set_input_active(False)
        editor.close()
