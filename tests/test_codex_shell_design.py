"""Non-Qt checks for the workbench shell's declarative theme contracts."""
from pathlib import Path
import ast
from melody_notation.qt_design import COLORS, stylesheet

ROOT = Path(__file__).resolve().parents[1]

def test_codex_style_shell_has_consistent_theme_tokens():
    for theme in COLORS:
        css=stylesheet(theme)
        for element in ('NavRail','Sidebar','EditorTabs','Inspector','AppMenuBar','VersionLabel','PropertyStack'):
            assert f'#{element}' in css
        assert COLORS[theme]['line'] in css

def test_workspace_shell_api_is_defined_without_changing_music_models():
    tree=ast.parse((ROOT/'src/qt_gui.py').read_text(encoding='utf-8'))
    main=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='MelodyMainWindow')
    methods={n.name for n in main.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
    assert {'_make_nav_rail','_make_sidebar','toggle_sidebar','toggle_inspector',
            'focus_search','_setup_menu','open_file','save_current'} <= methods
    # User assets and controller stay unchanged; no chat/reply panel built.
    assert (ROOT/'src/arrangement.py').is_file()
    # Keep the native titlebar and menubar; do not insert a second toolbar row.
    source=(ROOT/'src/qt_gui.py').read_text(encoding='utf-8')
    assert 'TopChrome' not in source
    assert 'self.tabs.setCornerWidget(self.inspector_toggle' in source
    assert 'self.statusBar().addPermanentWidget(self.version_label)' in source
    assert 'lay.addWidget(self.properties,0,Qt.AlignmentFlag.AlignTop)' in source
    assert (ROOT/'src/drums.py').is_file()
