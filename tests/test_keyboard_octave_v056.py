"""v0.5.6 keyboard range and transposed shortcut regressions."""
import os
import pytest

from melody_notation.piano_layout import (
    DEFAULT_START_OCTAVE, MIN_START_OCTAVE, MAX_START_OCTAVE,
    piano_key_layout, octave_offset, visible_note_range,
)
from melody_notation.performance import DEFAULT_KEYS, PerformanceSession, validate_mapping
from melody_notation.core import parse_text, blank_score_text


def test_default_c3_c5_and_wide_c6():
    assert DEFAULT_START_OCTAVE == 3
    base, width = piano_key_layout(857)
    assert (base[0], base[-1], width) == (48, 72, 57)
    wide, width = piano_key_layout(9999)
    assert (wide[0], wide[-1], width, len(wide)) == (48, 84, 57, 22)
    assert len(piano_key_layout(430)[0]) == 15


@pytest.mark.parametrize('start', range(MIN_START_OCTAVE, MAX_START_OCTAVE+1))
def test_all_octaves_shift_entire_visible_keyboard(start):
    base, _ = piano_key_layout(857, start)
    wide, _ = piano_key_layout(9999, start)
    assert (base[0], base[-1]) == (12 * (start+1), 12 * (start+3))
    assert wide[0] == base[0]
    assert wide[-1] == 12 * (start+4)
    assert (wide[0],wide[-1]) == visible_note_range(start, 22)
    assert DEFAULT_KEYS['A'] + octave_offset(start) == base[0]
    assert DEFAULT_KEYS['K'] + octave_offset(start) == 12 * (start+2)


@pytest.mark.parametrize('bad', [0, 6, 3.5, None, True, '3'])
def test_invalid_octave_selection_is_rejected(bad):
    with pytest.raises(ValueError):octave_offset(bad)


def test_transposed_key_maps_may_extend_beyond_original_editor_range():
    assert validate_mapping({'A':12}, min_pitch=0, max_pitch=127) == {'A':12}
    assert validate_mapping({'Z':108}, min_pitch=0, max_pitch=127) == {'Z':108}
    with pytest.raises(ValueError):validate_mapping({'A':12})
    with pytest.raises(ValueError):validate_mapping({'A':128}, min_pitch=0, max_pitch=127)


def test_pitch_recording_preserves_actual_octave():
    session = PerformanceSession(parse_text(blank_score_text(), strict=False))
    session.note_on(DEFAULT_KEYS['A'] + octave_offset(3), now=10.0)
    session.note_off(DEFAULT_KEYS['A'] + octave_offset(3), now=10.5)
    recorded = session.notation()
    assert recorded.measures[0][0].midi_pitch('C') == 48
    assert session.notes[0].pitch == 48


def test_qt_control_is_rightmost_persists_and_transposes(monkeypatch):
    pytest.importorskip('PySide6')
    os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QSettings
    from melody_notation.qt_gui import ScoreEditor
    from melody_notation.qt_piano import MappingDialog
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr('melody_notation.qt_piano.MidiInputRouter.set_active',lambda *a:None)
    settings=QSettings('MelodyNotation','Desktop')
    previous=settings.value('keyboard_start_octave',None)
    settings.setValue('keyboard_start_octave',3)
    widget=None
    try:
        widget=ScoreEditor(parse_text(blank_score_text(),strict=False))
        panel=widget.keyboard_panel
        toolbar=panel.toolbar
        assert toolbar._sections[-1] is panel.settings_button.parentWidget()
        assert panel.octave_up.parentWidget() is not panel.toolbar
        assert panel.contents.layout().itemAt(0).widget() is toolbar
        assert panel.octave_range.text()=='C3–C5'
        assert panel.pitch_for_key('A')==48
        assert panel.piano.mapping['A']==48
        assert panel.piano.LOW==48
        panel.set_start_octave(4)
        assert panel.pitch_for_key('A')==60
        assert panel.piano.LOW==60
        assert panel.octave_range.text()=='C4–C6'
        assert str(settings.value('keyboard_start_octave'))=='4'
        panel.set_start_octave(1)
        assert not panel.octave_down.isEnabled()
        assert panel.pitch_for_key('A')==24
        panel.set_start_octave(5)
        assert not panel.octave_up.isEnabled()
        assert panel.pitch_for_key('A')==72
        assert panel.piano.HIGH == 96 or panel.piano.HIGH == 108
        dlg=MappingDialog({'A':60}, 'dark', start_octave=3)
        try:
            assert dlg.grid.count()==37
            from PySide6.QtWidgets import QLabel
            assert any(label.text()=='C3' for label in dlg.grid.itemAt(0).widget().findChildren(QLabel))
        finally:dlg.close()
        # Changing octave must release physically held notes.
        called=[]
        monkeypatch.setattr(widget,'release_keys',lambda:called.append('released'))
        panel.set_start_octave(4)
        assert called==['released']
    finally:
        if widget:widget.close()
        if previous is None:settings.remove('keyboard_start_octave')
        else:settings.setValue('keyboard_start_octave',previous)
