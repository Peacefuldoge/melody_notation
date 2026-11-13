"""Optional smoke test for machines with PySide6 installed.

Run on Windows: python devtools/qt_gui_smoke.py
Run headlessly: QT_QPA_PLATFORM=offscreen python devtools/qt_gui_smoke.py
"""
from __future__ import annotations
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from PySide6.QtWidgets import QApplication

from melody_notation.core import parse_text
from melody_notation.workspace import ProjectWorkspace
from melody_notation.qt_gui import MelodyMainWindow, ScoreEditor, DrumEditor, TrackEditor

SCORE='title: 测试\nkey: C\ntime: 4/4\nbpm: 120\nnotes:\n| 1 2 3 5 |'


def main():
    app=QApplication.instance() or QApplication([])
    with TemporaryDirectory(prefix='melody-qt-smoke-') as t:
        project=ProjectWorkspace.create(Path(t),'测试工程')
        j=project.new_score('测试曲.jianpu',SCORE)
        d=project.new_asset('测试鼓.drum','drum')
        m=project.new_asset('测试编排.mtrack','mtrack')
        w=MelodyMainWindow(project.root)
        w.open_file(j);w.open_file(d);w.open_file(m)
        app.processEvents()
        assert sum(isinstance(x.widget,ScoreEditor) for x in w.open_docs)>=1
        assert any(isinstance(x.widget,DrumEditor) for x in w.open_docs)
        assert any(isinstance(x.widget,TrackEditor) for x in w.open_docs)
        w.toggle_theme()
        for doc in w.open_docs:
            if doc.path==j:
                w.tabs.setCurrentWidget(doc.widget)
                doc.widget._choose_note(1,1)
                doc.widget.replace_note(5,0,1,0,'')
                assert doc.dirty
                assert w.save_current()
                assert parse_text(j.read_text(encoding='utf-8')).measures[0][0].degree==5
                break
        for doc in w.open_docs:
            if doc.path==d:
                w.tabs.setCurrentWidget(doc.widget)
                doc.widget.toggle(0,1)
                assert w.save_current()
        assert w.project is not None and len(w.project.list_assets())==3
        assert w.tabs.count()>=3
        w.close();app.processEvents()
        print('PySide6 GUI smoke OK: multi-tab / score edit / drums / theme / save')


if __name__=='__main__':main()
