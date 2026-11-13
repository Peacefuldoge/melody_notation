"""Run with PySide6 installed, even on a headless CI host."""
import os
from pathlib import Path
import pytest
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
pytest.importorskip('PySide6')
from PySide6.QtWidgets import QApplication
from melody_notation.qt_gui import MelodyMainWindow


def test_open_demo_arrangement_and_animation_state():
    app=QApplication.instance() or QApplication([])
    root=Path(__file__).resolve().parents[1]
    demo=root/'demo_projects'/'我的第一份工程'
    window=MelodyMainWindow(demo)
    try:
        window.open_file(demo/'主题编排.mtrack')
        assert window._doc().kind=='mtrack'
        window._set_rendering(True)
        assert window._spinner_timer.isActive()
        assert window.play_button.text() in ('合成中…','Rendering…')
        previous=window._spinner_phase
        window._spin_preview_icon()
        assert window._spinner_phase==(previous+1)%12
        window.stop()
        assert not window._spinner_timer.isActive()
        assert window.play_button.text() in ('播放','Play')
    finally:
        window.close()
