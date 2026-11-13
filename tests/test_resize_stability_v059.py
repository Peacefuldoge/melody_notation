"""v0.5.9 regression: prevent recursive native-Qt layout changes."""
from __future__ import annotations

import ast
import faulthandler
from pathlib import Path
import sys

import pytest


def _class(source, name):
    for node in ast.parse(source).body:
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    raise AssertionError(f'Class {name} not found')


def _method(node, name):
    for child in node.body:
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == name:
            return child
    raise AssertionError(f'Method {name} not found')


def test_native_resize_handlers_do_not_resize_their_own_geometry():
    root = Path(__file__).resolve().parents[1] / 'src'
    for file, cls in [('qt_piano.py', 'ResponsivePianoScrollArea'),
                      ('qt_gui.py', 'ScoreCanvas')]:
        source = (root / file).read_text(encoding='utf-8')
        method = _method(_class(source, cls), 'resizeEvent')
        called = [n.func.attr for n in ast.walk(method)
                  if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
        assert 'setFixedHeight' not in called
        assert 'setFixedSize' not in called
        assert 'setGeometry' not in called
        assert 'resize' not in called
    keyboard = (root / 'qt_piano.py').read_text(encoding='utf-8')
    adaptive = _class(keyboard, 'AdaptivePerformanceToolbar')
    assert not any(isinstance(n, ast.FunctionDef) and n.name == 'resizeEvent'
                   for n in adaptive.body)
    assert '_StableWrapLayout' in keyboard
    assert 'line.deleteLater()' not in keyboard


def test_crash_log_defaults_to_local_app_data(monkeypatch, tmp_path):
    from melody_notation.diagnostics import crash_log_path
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    assert crash_log_path() == tmp_path / 'MelodyNotation' / 'logs' / 'crash.log'


def test_gui_crash_log_is_repeatable_and_writes_tracebacks(tmp_path):
    from melody_notation import diagnostics
    previous = sys.excepthook
    log = tmp_path / 'logs' / 'crash.log'
    try:
        assert diagnostics.enable_gui_crash_log(log) == log
        assert diagnostics.enable_gui_crash_log(log) == log
        assert log.exists()
        data = log.read_text(encoding='utf-8')
        assert 'GUI session' in data
    finally:
        faulthandler.disable()
        sys.excepthook = previous
        if diagnostics._log_handle is not None:
            diagnostics._log_handle.close()
        diagnostics._log_handle = None
        diagnostics._original_excepthook = None


def test_qt_resize_stress_no_tool_overlap(monkeypatch):
    pytest.importorskip('PySide6')
    from PySide6.QtWidgets import QApplication
    from melody_notation.core import blank_score_text, parse_text
    from melody_notation.qt_gui import ScoreEditor
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr('melody_notation.qt_piano.MidiInputRouter.set_active', lambda *_: None)
    editor = ScoreEditor(parse_text(blank_score_text(), strict=False))
    editor.resize(1100, 840)
    editor.show()
    app.processEvents()
    try:
        panel = editor.keyboard_panel
        for i in range(80):
            editor.resize((1400, 1080, 800, 580, 410, 900)[i % 6],
                          (760, 680, 900, 600)[i % 4])
            app.processEvents()
            if i % 7 == 0:
                panel.settings_button.click()
                app.processEvents()
            if i % 11 == 0:
                panel.scroller._fit_keyboard()
            app.processEvents()
            rects = [w.geometry() for w in panel.toolbar._sections]
            assert 1 <= panel.toolbar.row_count <= 3
            for a, r in enumerate(rects):
                assert r.x() >= 0 and r.right() <= panel.toolbar.width()
                for other in rects[a+1:]:
                    assert not r.intersects(other), (i, r, other)
    finally:
        panel.settings_dialog.close()
        editor.set_input_active(False)
        editor.close()
