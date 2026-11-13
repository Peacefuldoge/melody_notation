"""Regression tests for responsive keyboard expansion."""
from __future__ import annotations

import os

from melody_notation.piano_layout import (
    BASE_WHITE_COUNT, DEFAULT_WHITE_WIDTH, MAX_HIGH,
    MIN_WHITE_WIDTH, piano_key_layout,
)
from melody_notation.performance import validate_mapping


def test_default_two_octaves_then_show_more_notes_on_right():
    base, width = piano_key_layout(857)
    assert len(base) == BASE_WHITE_COUNT == 15
    assert (base[0], base[-1], width) == (48, 72, 57)

    # A new white note appears only once it can fit at a normal key width.
    partial, width = piano_key_layout(914)
    assert partial[:-1] == base
    assert partial[-1] == 74  # D5; C#6 also becomes visible in the painter
    assert width == DEFAULT_WHITE_WIDTH

    medium, width = piano_key_layout(1200)
    assert medium[-1] == 83  # B5
    assert len(medium) == 21

    full, width = piano_key_layout(1256)
    assert len(full) == BASE_WHITE_COUNT + 7
    assert full[-1] == MAX_HIGH - 12 == 84  # C6, default C3 shift


def test_wide_editor_never_exceeds_an_additional_octave():
    full, width = piano_key_layout(1256)
    assert piano_key_layout(9999) == (full, width)


def test_narrow_editor_preserves_base_notes_and_scroll_fallback():
    narrow, width = piano_key_layout(650)
    assert len(narrow) == 15 and narrow[-1] == 72
    assert MIN_WHITE_WIDTH <= width < DEFAULT_WHITE_WIDTH
    tiny, width = piano_key_layout(430)
    assert tiny == narrow
    assert width == MIN_WHITE_WIDTH
    assert len(tiny) * width + 1 > 430  # horizontal scroll


def test_extended_range_is_customizable_and_existing_keys_stay_unchanged():
    assert validate_mapping({'Z': 96}) == {'Z': 96}
    from melody_notation.performance import DEFAULT_KEYS
    assert DEFAULT_KEYS['A'] == 60
    assert DEFAULT_KEYS['K'] == 72


def test_qt_keyboard_expands_and_mapping_dialog_offers_c7(monkeypatch):
    import pytest
    pytest.importorskip('PySide6')
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    from PySide6.QtWidgets import QApplication
    from melody_notation.qt_piano import MappingDialog, PianoKeys

    app = QApplication.instance() or QApplication([])
    piano = PianoKeys()
    try:
        on, off = [], []
        piano.note_on.connect(lambda p, v: on.append((p, v)))
        piano.note_off.connect(lambda p: off.append(p))
        piano.fit_to_width(1300)
        assert piano.HIGH == 84
        assert len(piano.whites) == 22
        assert piano._hit(piano.width() - 15, 100) == 84
        piano.fit_to_width(650)
        assert piano.HIGH == 72
        assert len(piano.whites) == 15
        assert piano.width() <= 650

        dialog = MappingDialog({'Z': 96}, 'dark')
        try:
            # 37 MIDI notes C4..C7, including all black keys.
            assert dialog.grid.count() == 37
            assert dialog.mapping_scroll.widget() is not None
        finally:
            dialog.close()
    finally:
        piano.close()
