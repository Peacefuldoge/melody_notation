"""Windows/offscreen PySide6 layout smoke test. Uses a disposable project."""
from pathlib import Path
from tempfile import TemporaryDirectory
from PySide6.QtWidgets import QApplication, QListWidget
from PySide6.QtCore import Qt, QSettings
from melody_notation.qt_gui import MelodyMainWindow
from melody_notation.workspace import ProjectWorkspace


def main():
    app=QApplication.instance() or QApplication([])
    with TemporaryDirectory(prefix='melody-layout-test-') as tmp:
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,QSettings.Scope.UserScope,tmp)
        project=ProjectWorkspace.create(Path(tmp),'Music project')
        score=project.new_score('melody.jianpu',
            'title: Melody\nkey: C\ntime: 4/4\nbpm: 120\nnotes:\n| 1 2 3 5 |')
        drums=project.new_asset('beat.drum','drum')
        tracks=project.new_asset('mix.mtrack','mtrack')
        w=MelodyMainWindow(project.root)
        w.show();app.processEvents()
        assert w.rail.width()==54
        assert w.tabs.cornerWidget(Qt.Corner.TopRightCorner) is w.inspector_toggle
        assert not w.findChildren(type(w.inspector), 'TopChrome')
        assert w.version_label.text() == 'Melody Notation v0.4.9'
        assert w.version_label.isVisible()
        assert w.properties.height() < w.inspector.height() - 30, 'Property card should not stretch'
        assert w.sidebar.isVisible() and w.inspector.isVisible()
        assert w.menuBar().actions(), 'File/Edit/View/Export/Help menu missing'
        assert isinstance(w.recent_selector,QListWidget)
        assert w.new_menu_button.menu() is not None
        assert w.rail_new.menu() is not None
        w.open_file(score);w.open_file(drums);w.open_file(tracks)
        assert w.tabs.count()>=3
        w.toggle_sidebar();app.processEvents()
        assert not w.sidebar.isVisible() and w.rail.isVisible()
        w.toggle_sidebar();app.processEvents()
        assert w.sidebar.isVisible()
        w.toggle_inspector();app.processEvents()
        assert not w.inspector.isVisible()
        assert w.version_label.isVisible(), 'Version should survive inspector hiding'
        w.toggle_inspector();app.processEvents()
        assert w.inspector.isVisible()
        for theme in ('light','dark','beige','olive'):
            w.theme=theme;w._apply_theme();app.processEvents()
        w.focus_search();assert w.search.hasFocus()
        w.close();app.processEvents()
    print('PySide6 Codex-style layout smoke OK')

if __name__=='__main__':main()
