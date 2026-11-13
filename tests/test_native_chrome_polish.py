"""Regression checks for native Windows caption colors and flat Qt stepper UI."""
import ctypes
from pathlib import Path

import pytest

from melody_notation import qt_design


def test_caption_color_converts_to_windows_colorref():
    assert qt_design._win32_colorref('#123456') == 0x563412
    assert qt_design._win32_colorref('#EDEFE5') == 0xE5EFED
    with pytest.raises(ValueError):
        qt_design._win32_colorref('bad')


def test_spin_buttons_are_flat_and_theme_aware():
    for theme in qt_design.COLORS:
        css = qt_design.stylesheet(theme)
        assert 'QSpinBox::up-button' in css
        assert 'QDoubleSpinBox::down-button' in css
        assert 'border: none; background: transparent;' in css
        assert 'QToolButton::menu-indicator {image: none;' in css
        assert qt_design.COLORS[theme]['soft'] in css


def test_action_menus_do_not_need_dropdown_markers():
    source = (Path(__file__).resolve().parents[1] / 'src' / 'qt_gui.py').read_text(encoding='utf-8')
    assert '.setPopupMode(' not in source
    assert '.setMenu(' not in source
    for name in ('self.rail_new', 'self.new_menu_button', 'self.operations'):
        assert f'{name}.clicked.connect(' in source
    for menu in ('project_menu', 'new_menu', 'rail_menu'):
        assert f'{menu}.popup(' in source


def test_windows_native_chrome_matches_selected_theme(monkeypatch):
    calls = []

    class FakeSetter:
        def __call__(self, hwnd, attr, value, size):
            index = int(attr)
            calls.append((index, ctypes.cast(value, ctypes.POINTER(ctypes.c_uint32)).contents.value))
            return 0

    class FakeDwm:
        DwmSetWindowAttribute = FakeSetter()

    monkeypatch.setattr(qt_design.sys, 'platform', 'win32')
    monkeypatch.setattr(ctypes, 'WinDLL', lambda _: FakeDwm(), raising=False)

    class FakeWindow:
        def winId(self):
            return 4321

    for theme in qt_design.COLORS:
        calls.clear()
        assert qt_design.apply_native_chrome(FakeWindow(), theme, True)
        observed = dict(calls)
        assert observed[38] == 3  # Acrylic requested
        assert observed[35] == qt_design._win32_colorref(qt_design.COLORS[theme]['window'])
        assert observed[36] == qt_design._win32_colorref(qt_design.COLORS[theme]['ink'])
        assert observed[34] == qt_design._win32_colorref(qt_design.COLORS[theme]['line'])
        assert observed[20] == (1 if theme == 'dark' else 0)
    calls.clear()
    qt_design.apply_native_chrome(FakeWindow(), 'olive', False)
    assert dict(calls)[38] == 1  # No material when user disabled it
