"""Integration smoke test: UI navigation follows both themes without losing state."""
from pathlib import Path
from tempfile import TemporaryDirectory
from PIL import ImageGrab
import os
import tkinter as tk
from melody_notation.gui import Editor
from melody_notation.workspace import ProjectWorkspace

out = Path(__file__).resolve().parents[1] / 'output'
out.mkdir(exist_ok=True)
with TemporaryDirectory() as td:
    os.environ['MELODY_RECENT_PROJECTS_FILE'] = str(Path(td) / 'recent.json')
    root=tk.Tk()
    root.geometry('1500x850+32+32')
    app=Editor(root)
    project=ProjectWorkspace.create(Path(td), 'Melody Studio')
    project.new_score('旋律草稿.jianpu', app._blank_score_text('旋律草稿'))
    project.new_score('配乐草稿.jianpu', app._blank_score_text('配乐草稿'))
    app.project=project
    app._register_project(project.root)
    app.refresh_project_tree()
    root.update()
    assert app.NAV_BG == app.palette['surface']
    assert app.project_border.cget('bg') == app.palette['window']
    assert app.nav_panel.cget('bg') == app.palette['surface']
    assert app.nav_search_entry.cget('bg') == app.palette['raised']
    app.nav_search.set('旋律')
    root.update()
    assert app._tree_item_for(project.root / '旋律草稿.jianpu')
    app.nav_search.set('')
    root.update()
    app.redraw();root.update()
    ImageGrab.grab(bbox=(32,32,1532,882)).save(out/'sidebar-theme-light.png')

    text_before=app.edit.get('1.0','end-1c')
    tabs_before=list(app.documents)
    app.toggle_theme()
    root.update()
    assert app.NAV_BG == app.palette['surface']
    assert app.NAV_RAIL == app.palette['window']
    assert app.nav_panel.cget('bg') == app.palette['surface']
    assert app.nav_rail.cget('bg') == app.palette['window']
    assert app.nav_search_entry.cget('bg') == app.palette['raised']
    assert app.search_hint.cget('fg') == app.palette['secondary']
    assert app.edit.get('1.0','end-1c')==text_before
    assert app.documents==tabs_before
    app.redraw();root.update()
    ImageGrab.grab(bbox=(32,32,1532,882)).save(out/'sidebar-theme-dark.png')

    app.toggle_project_sidebar();root.update()
    assert not app.nav_panel.winfo_ismapped()
    app.toggle_theme();root.update()
    assert not app.nav_panel.winfo_ismapped()
    app.toggle_project_sidebar();root.update()
    assert app.nav_panel.winfo_ismapped()
    assert app.nav_panel.cget('bg')==app.palette['surface']
    app.nav_search_entry.focus_set();root.update()
    assert app.nav_search_entry.cget('insertbackground')==app.palette['text']
    # Hover leaves should restore the CURRENT theme, even after switching.
    nav_button=app.nav_file_button
    nav_button.event_generate('<Enter>');root.update()
    assert nav_button.cget('bg')==app.palette['hover']
    nav_button.event_generate('<Leave>');root.update()
    assert nav_button.cget('bg')==app.palette['surface']
    root.destroy()
print('Sidebar theme smoke passed')
