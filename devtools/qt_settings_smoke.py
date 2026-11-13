"""Run on your Windows Conda environment: python devtools/qt_settings_smoke.py

Offscreen CI: set QT_QPA_PLATFORM=offscreen before launching. Does not touch
personal projects; uses temporary QSettings storage and an isolated project.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings
from melody_notation.workspace import ProjectWorkspace
from melody_notation.qt_gui import MelodyMainWindow
from melody_notation.qt_preferences import PreferencesDialog
from melody_notation.qt_design import COLORS


def main():
    app=QApplication.instance() or QApplication([])
    with TemporaryDirectory(prefix='melody-settings-') as temp:
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,QSettings.Scope.UserScope,temp)
        project=ProjectWorkspace.create(Path(temp),'UI smoke project')
        path=project.new_score('test.jianpu',
            'title: Test\nkey: C\ntime: 4/4\nbpm: 120\nnotes:\n| 1 2 3 5 |')
        w=MelodyMainWindow(project.root);w.show();app.processEvents()
        w.open_file(path)
        doc=w._doc()
        assert doc is not None and doc.path==path
        for theme in COLORS:
            w.theme=theme;w._apply_theme();app.processEvents()
            assert doc.widget.theme==theme
            assert not doc.widget.canvas.image.isNull()
        w.language='en';w._apply_language();app.processEvents()
        assert w.settings_button.toolTip()=='Settings'
        assert w.property_stack.count()==4
        dialog=PreferencesDialog(w,theme='olive',language='en',directory=temp)
        values=dialog.values()
        assert values['theme']=='olive' and values['language']=='en'
        assert values['default_save_directory']==str(Path(temp).resolve())
        dialog.close()
        w.default_save_directory=temp
        assert w._preferred_dir()==Path(temp)
        w.settings.setValue('theme','beige');w.settings.setValue('language','en')
        w.settings.sync()
        w.close();app.processEvents()
        settings=QSettings('MelodyNotation','Desktop')
        assert settings.value('theme')=='beige' and settings.value('language')=='en'
    print('Qt v0.4.1 settings smoke passed')

if __name__=='__main__':main()
