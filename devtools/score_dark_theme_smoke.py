"""Capture real light/dark Tk score previews and verify correct theme swapping.

Run with: xvfb-run -a python devtools/score_dark_theme_smoke.py
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import os
import tkinter as tk
from PIL import ImageGrab
from melody_notation.gui import Editor
from melody_notation.png import SCORE_THEMES

output = Path(__file__).resolve().parents[1] / 'output'
output.mkdir(exist_ok=True)
with TemporaryDirectory() as folder:
    os.environ['MELODY_RECENT_PROJECTS_FILE'] = str(Path(folder)/'recents.json')
    root = tk.Tk()
    root.geometry('1500x870+25+25')
    app = Editor(root)
    root.update()
    app.open_sample_tab('huang.jianpu')
    app.selected = (1, 3)
    app.redraw()
    root.update()
    assert app.theme_mode == 'light'
    ImageGrab.grab(bbox=(25,25,1525,895)).save(output/'score-light-workspace.png')
    app.toggle_theme()
    root.update()
    assert app.theme_mode == 'dark'
    assert app.photo is not None
    dark_tk_image = app.photo
    assert app.score_model.title == '荒'
    assert app.selected == (1,3)
    ImageGrab.grab(bbox=(25,25,1525,895)).save(output/'score-dark-workspace.png')
    app.toggle_theme()
    root.update()
    assert app.theme_mode == 'light'
    assert app.score_model.title == '荒'
    assert app.selected == (1,3)
    root.destroy()
print('score dark theme GUI smoke passed')
