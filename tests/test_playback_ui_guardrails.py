"""Playback UI regressions validated statically if PySide6 is not installed in CI.

The optional Qt UI is exercised interactively on Windows where a real audio
output device is available. These checks also guard the source wiring.
"""
from pathlib import Path
from melody_notation.qt_design import stylesheet, COLORS


def test_right_inspector_cards_have_no_section_titles():
    source=(Path(__file__).resolve().parents[1]/'src'/'qt_gui.py').read_text(encoding='utf-8')
    assert "QGroupBox('试听控制')" not in source
    assert "QGroupBox('编辑属性')" not in source
    assert "playbox=QFrame();playbox.setObjectName('InspectorCard')" in source
    assert "self.properties=QFrame();self.properties.setObjectName('InspectorCard')" in source
    for theme in COLORS:
        assert 'QFrame#InspectorCard' in stylesheet(theme)


def test_windows_plays_direct_wav_with_qt_fallback_and_explicit_error():
    source=(Path(__file__).resolve().parents[1]/'src'/'qt_gui.py').read_text(encoding='utf-8')
    assert 'WindowsMCIPlayer()' in source
    assert 'player.load_file(wav)' in source
    assert 'player.play()' in source
    assert 'self.media.setSource(QUrl.fromLocalFile(str(wav)))' in source
    assert "self._playback_failure('合成音频失败：'+exc)" in source
    assert 'QMessageBox.warning(self' in source
    assert 'self._mci_timer.timeout.connect(self._refresh_mci)' in source
