"""Full Tk smoke test for v0.2.11, including actual screenshots.

Run with: xvfb-run -a python devtools/sidebar_cleanup_smoke.py
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import os
import tkinter as tk
from PIL import ImageGrab
from melody_notation.gui import Editor

out = Path(__file__).resolve().parents[1] / 'output'
out.mkdir(parents=True, exist_ok=True)

with TemporaryDirectory() as folder:
    os.environ['MELODY_RECENT_PROJECTS_FILE'] = str(Path(folder) / 'recents.json')
    root = tk.Tk()
    root.geometry('1500x870+25+25')
    ed = Editor(root)
    root.update()
    ed.open_sample_tab('huang.jianpu')
    ed.redraw()
    root.update()
    assert ed.nav_file_button.winfo_ismapped()
    assert ed.nav_edit_button.winfo_ismapped()
    assert ed.nav_export_button.winfo_ismapped()
    assert ed.nav_tools_button.winfo_ismapped()
    assert not hasattr(ed, 'nav_more_button')
    assert not hasattr(ed, 'focus_project_home')
    assert not ed.nav_rail_new_button.winfo_ismapped()
    assert not ed.nav_rail_menu_button.winfo_ismapped()
    assert not any(isinstance(w, tk.Button) and '保存' in w.cget('text')
                   for w in ed.nav_panel.winfo_children())
    menu = ed._build_file_actions_menu()
    names = [menu.entrycget(i,'label') for i in range(menu.index('end') + 1)
             if menu.type(i) != 'separator']
    assert sum('另存为' in name for name in names) == 1
    assert sum(name.startswith('保存') for name in names) == 1
    assert ed.score_model.title == '荒'
    ImageGrab.grab(bbox=(25,25,1525,895)).save(out/'navigation-clean-light.png')
    ed.toggle_theme()
    root.update()
    assert ed.nav_file_button.cget('bg') == ed.palette['surface']
    ImageGrab.grab(bbox=(25,25,1525,895)).save(out/'navigation-clean-dark.png')
    ed.toggle_project_sidebar()
    root.update()
    assert not ed.nav_panel.winfo_ismapped()
    assert ed.nav_rail_new_button.winfo_ismapped()
    assert ed.nav_rail_menu_button.winfo_ismapped()
    ed.toggle_project_sidebar()
    root.update()
    assert ed.nav_panel.winfo_ismapped()
    assert not ed.nav_rail_new_button.winfo_ismapped()
    assert not ed.nav_rail_menu_button.winfo_ismapped()
    root.destroy()
print('v0.2.11 sidebar cleanup smoke passed')
