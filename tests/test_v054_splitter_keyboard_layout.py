"""Regression checks for the v0.5.4 navigation and performance toolbar fixes."""
from __future__ import annotations

import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest

from melody_notation.layout_ops import navigation_width_limits


def test_navigation_pane_respects_the_sidebar_width_limits():
    assert navigation_width_limits(54, 206, 345) == (260, 399)
    assert navigation_width_limits(60, 100, 250) == (160, 310)
    assert navigation_width_limits(54, 270, 200) == (324, 324)


def test_gui_splitter_drag_cannot_create_a_blank_nav_shell(monkeypatch):
    pytest.importorskip('PySide6')
    from PySide6.QtWidgets import QApplication
    from melody_notation.qt_gui import MelodyMainWindow
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr('melody_notation.qt_gui.load_recent_projects', lambda: [])
    monkeypatch.setattr(MelodyMainWindow, 'open_sample', lambda self: None)
    window = MelodyMainWindow()
    window.show()
    app.processEvents()
    try:
        assert window.nav_shell.minimumWidth() == 260
        assert window.nav_shell.maximumWidth() == 399
        # Attempt to drag farther than the sidebar can fill.
        window.sides.setSizes([800, 300, 280])
        app.processEvents()
        assert 260 <= window.nav_shell.width() <= 399
        assert window.sidebar.isVisible()
        assert window.nav_shell.width() <= window.rail.width() + window.sidebar.maximumWidth()
        window.toggle_sidebar()
        app.processEvents()
        assert window.nav_shell.width() == window.rail.width()
        window.toggle_sidebar()
        app.processEvents()
        assert 260 <= window.nav_shell.width() <= 399
    finally:
        window.close()


def test_keyboard_toolbar_is_compact_and_keys_fit_the_editor(monkeypatch):
    pytest.importorskip('PySide6')
    from PySide6.QtWidgets import QApplication
    from melody_notation.core import blank_score_text, parse_text
    from melody_notation.qt_gui import ScoreEditor
    from melody_notation.qt_piano import PianoKeys
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr('melody_notation.qt_piano.MidiInputRouter.set_active', lambda *a: None)
    editor = ScoreEditor(parse_text(blank_score_text(), strict=False))
    editor.resize(750, 600)
    editor.show()
    app.processEvents()
    try:
        panel = editor.keyboard_panel
        bar = panel.toolbar
        assert bar is not None
        assert panel.keyboard_instrument.parentWidget() is not None
        assert panel.keyboard_instrument.parentWidget() not in bar._sections
        assert len(bar._sections) == 3
        assert not hasattr(panel, "toolbar_scroll")
        assert not hasattr(panel, 'device_status')
        assert panel.keyboard_instrument.count() > 0
        assert panel.keyboard_instrument.currentText() == editor.live_instrument
        panel.set_device_status('已连接 MIDI：测试设备')
        assert '测试设备' in panel.devices.toolTip()
        piano = panel.piano
        piano.fit_to_width(650)
        assert piano.width() <= 650
        assert piano.white_width <= PianoKeys.WHITE_WIDTH
        piano.fit_to_width(430)
        assert piano.white_width == 33
        assert piano.width() > 430  # Scroll only for a genuinely narrow editor.
        piano.fit_to_width(1200)
        assert piano.white_width == PianoKeys.WHITE_WIDTH
    finally:
        editor.set_input_active(False)
        editor.close()
