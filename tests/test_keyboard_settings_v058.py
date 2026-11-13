"""v0.5.10 regression: grouped non-modal settings, not six toolbar clusters."""
from __future__ import annotations

import os
from pathlib import Path

import pytest


def test_version_and_settings_dialog_components_are_kept_in_source():
    from melody_notation import __version__
    assert __version__ == '0.5.10'
    source = Path(__file__).resolve().parents[1].joinpath('src/qt_piano.py').read_text(encoding='utf-8')
    assert 'class PerformanceSettingsDialog(QDialog)' in source
    assert "self.toolbar.set_sections((record_group, devices_group, settings_group))" in source
    assert "self.settings_button = QPushButton('⚙ 演奏设置')" in source
    assert "self.settings_dialog = PerformanceSettingsDialog(self)" in source


def test_qt_settings_dialog_controls_and_lifecycle(monkeypatch):
    pytest.importorskip('PySide6')
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    from PySide6.QtWidgets import QApplication, QDialog
    from melody_notation.qt_gui import ScoreEditor
    from melody_notation.core import parse_text, blank_score_text
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr('melody_notation.qt_piano.MidiInputRouter.set_active', lambda *_: None)
    editor = ScoreEditor(parse_text(blank_score_text(), strict=False))
    editor.show()
    app.processEvents()
    try:
        panel = editor.keyboard_panel
        bar = panel.toolbar
        assert len(bar._sections) == 3
        assert isinstance(panel.settings_dialog, QDialog)
        assert not panel.settings_dialog.isModal()
        assert panel.settings_button.parentWidget() in bar._sections
        assert panel.keyboard_instrument.parentWidget() not in bar._sections
        assert panel.monitor_level.parentWidget() not in bar._sections
        assert panel.octave_up.parentWidget() not in bar._sections
        assert not panel.settings_dialog.isVisible()
        panel.settings_button.click()
        app.processEvents()
        assert panel.settings_dialog.isVisible()
        assert panel.settings_button.isChecked()
        assert panel.keyboard_instrument.isVisible()
        panel.keyboard_instrument.setCurrentText('flute')
        assert editor.live_instrument == 'flute'
        panel.monitor_level.setValue(42)
        assert panel.settings_dialog.monitor_value.text() == '42%'
        assert abs(editor._live_audio.volume - .42) < 1e-9
        panel.set_start_octave(3, persist=False)
        panel.octave_up.click()
        assert panel.octave_range.text() == 'C4–C6'
        panel.set_device_status('已连接 MIDI：测试乐器')
        assert '测试乐器' in panel.settings_dialog.device_state.text()
        panel.settings_dialog.close()
        app.processEvents()
        assert not panel.settings_button.isChecked()
        panel.settings_button.click()
        assert panel.settings_dialog.isVisible()
        panel.toggle.setChecked(False)
        assert not panel.settings_dialog.isVisible()
        assert not panel.settings_button.isChecked()
    finally:
        editor.set_input_active(False)
        editor.close()


def test_toolbar_reflows_only_three_groups():
    from melody_notation.piano_layout import toolbar_row_groups
    widths = (112, 218, 124)
    assert toolbar_row_groups(600, widths) == ((0, 1, 2),)
    assert toolbar_row_groups(380, widths) == ((0, 1), (2,))
    assert toolbar_row_groups(245, widths) == ((0,), (1,), (2,))
